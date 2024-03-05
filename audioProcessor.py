import time
import wave
from definitions import OUTPUT_AUDIO_DEVICE
import numpy as np
import pyaudio


class AudioProcessor:
    def __init__(self, chunk_size=256, sample_rate=44100, audio_callback=None):
        self.chunk_size = chunk_size
        self.fs = sample_rate
        self.callback = audio_callback

        self.pya = pyaudio.PyAudio()
        self.stream: pyaudio.Stream or None = None
        self.is_playing = False

        self.output_device_id = 0
        self.config_device()

    def __del__(self):
        self.terminate()

    def terminate(self):
        self.stop()
        self.pya.terminate()

    def config_device(self):
        print("----------------------device list---------------------")
        info = self.pya.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        for i in range(num_devices):
            if (self.pya.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = self.pya.get_device_info_by_host_api_device_index(0, i).get('name')
                print(name)
                if name == OUTPUT_AUDIO_DEVICE:
                    self.output_device_id = i
                    print(f"Output device set to '{name}' with id {self.output_device_id}")
        print("-------------------------------------------------------------")

    @staticmethod
    def dtype2width(dtype) -> int:
        """
        For a given dtype, return number of "bits"
        :param dtype: can be np.int16 or float
        :return: number of bits
        """
        if dtype == float or dtype == pyaudio.paFloat32:
            return 32
        if dtype == np.int16 or dtype == pyaudio.paInt16:
            return 16
        return -1

    @staticmethod
    def width2dtype(width):
        if width == 2:
            return np.int16
        return float

    # refer: https://stackoverflow.com/questions/22636499/convert-multi-channel-pyaudio-into-numpy-array
    @staticmethod
    def decode(data, channels, dtype):
        """
        Convert a byte stream into a 2D numpy array with
        shape (chunk_size, channels)

        Samples are interleaved, so for a stereo stream with left channel
        of [L0, L1, L2, ...] and right channel of [R0, R1, R2, ...], the output
        is ordered as [L0, R0, L1, R1, ...]
        """
        result = np.frombuffer(data, dtype=dtype)

        w = AudioProcessor.dtype2width(dtype)
        result = result.astype(float) / (2 ** (w - 1))

        assert len(result) % channels == 0
        chunk_length = len(result) // channels

        return result.reshape((chunk_length, channels))

    @staticmethod
    def encode(data, dtype):
        """
        Convert a 2D numpy array into a byte stream for PyAudio
        Signal should be a numpy array with shape (chunk_size, channels)
        """
        interleaved = data.flatten()
        w = AudioProcessor.dtype2width(dtype)
        interleaved = interleaved * (2 ** (w - 1))
        return interleaved.astype(dtype).tobytes()

    def play(self, audio_file_path: str, delay_ms=0):
        delay_gestures = delay_ms < 0
        delay = abs(delay_ms / 1000.0)
        self.is_playing = True
        play_idx = 0
        with wave.open(audio_file_path, "rb") as wf:
            if wf.getframerate() != self.fs:
                print(f"Warning: Sample rate mismatch. ({self.fs}), ({wf.getframerate()})")
            self.stream = self.pya.open(rate=self.fs,
                                        channels=wf.getnchannels(),
                                        format=self.pya.get_format_from_width(wf.getsampwidth()),
                                        input=False, output=True,
                                        frames_per_buffer=self.chunk_size)

            chunk_duration_sec = self.chunk_size / self.fs
            num_dly_chunks = int(round(delay / chunk_duration_sec))
            zeros = np.zeros((self.chunk_size * wf.getnchannels()), dtype=np.int16)

            data = zeros if play_idx < num_dly_chunks and not delay_gestures else wf.readframes(self.chunk_size)
            while len(data) and self.is_playing:
                if self.callback and not delay_gestures:
                    dtype = self.width2dtype(wf.getsampwidth())
                    data = self.decode(data, wf.getnchannels(), dtype)
                    data = self.callback(data)
                    data = self.encode(data, dtype)
                self.stream.write(data)
                data = zeros if play_idx < num_dly_chunks and not delay_gestures else wf.readframes(self.chunk_size)
                play_idx += 1
                if play_idx >= num_dly_chunks:
                    delay_gestures = False

    def stop(self):
        self.is_playing = False
        if self.stream:
            self.stream.close()
