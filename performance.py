import numpy as np
import os
import glob
import signal
from typing import List, Tuple
from shimi import Shimi, Command
from definitions import *
from audioProcessor import AudioProcessor
from networkHandler import NetworkCommand, NetworkHandler
import threading
from util import Util


class Performance:
    def __init__(self, chunk_size=256, sample_rate=44100):
        self.chunk_size = chunk_size
        self.fs = sample_rate
        self.audio_processor = AudioProcessor(chunk_size=self.chunk_size,
                                              sample_rate=sample_rate,
                                              audio_callback=self.callback)
        self.shimi = Shimi(LIMITS)
        self.udp = NetworkHandler(UDP_PORT, self.network_callback, timeout_sec=0.25)
        self.gestures = []
        self.gesture_idx = 0
        self.play_idx = 0

        self.audio_file = None
        self.gesture_file = None
        self.tempo = 120

        self.thread = threading.Thread(target=self.perform_thread_handler)
        signal.signal(signal.SIGINT, self.sig_handle)
        self.shimi.start()
        self.udp.start()

    def __del__(self):
        self.terminate()

    def sig_handle(self, num, frame):
        self.terminate()

    def terminate(self):
        self.audio_processor.terminate()
        self.udp.terminate()
        self.shimi.terminate()

    def preprocess_gesture_data(self, gesture_file):
        # DS: [motor id, start beat absolute, position (0, 1), length in beats]
        # Convert float values to int. beats -> samples, pos (0, 1) -> (0, 100)

        raw_data = np.loadtxt(gesture_file, delimiter=',')

        # Sort gestures in terms of their start times
        g = raw_data[raw_data[:, 1].argsort()]

        def beats2sec(beats):
            return beats * (60 / self.tempo)

        for i, line in enumerate(g):
            self.gestures.append(Command(dxl_id=int(line[0]) - 1,
                                         angle=line[2],
                                         start_time=beats2sec(line[1]),
                                         duration=line[3]))

    def perform(self, audio_path: str, gesture_file: str, tempo: float):
        self.tempo = tempo
        self.preprocess_gesture_data(gesture_file)
        self.audio_processor.play(audio_path)
        self.stop()

    def stop(self):
        self.audio_processor.stop()
        if self.thread.is_alive():
            self.thread.join()
        self.shimi.stop()

    def perform_thread_handler(self):
        self.perform(self.audio_file, self.gesture_file, self.tempo)

    def callback(self, data: np.ndarray):
        # Haptic vibrations
        data[:, 0] = np.mean(data, axis=1)
        # data[:, 1] = Util.zero_lpf(data[:, 0], 0.9)
        data[:, 1] = Util.biquad_lpf(data[:, 0], fc=200, fs=self.fs)

        # Motor actuations
        l = self.play_idx * self.chunk_size / self.fs
        r = (self.play_idx + 1) * self.chunk_size / self.fs

        if self.gesture_idx < len(self.gestures):
            cmd = self.gestures[self.gesture_idx]

            # Add all the commands within this frame to the queue
            while l <= cmd.start_time < r:
                self.shimi.append_command(cmd)
                self.gesture_idx += 1
                if self.gesture_idx >= len(self.gestures):
                    break
                cmd = self.gestures[self.gesture_idx]

        self.play_idx += 1
        return data

    def network_callback(self, command: NetworkCommand, data):
        if command == NetworkCommand.START:
            self.audio_file, self.gesture_file, self.tempo = data
            if self.thread.is_alive():
                print("Performance in progress. New performance cannot be accepted yet...")
            else:
                self.thread.start()
        elif command == NetworkCommand.STOP:
            self.stop()
