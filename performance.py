import numpy as np
import os
import signal
from shimi import Shimi, Command
from definitions import *
from audioProcessor import AudioProcessor
from networkHandler import NetworkCommand, NetworkHandler
import threading
from util import Util
from song import Song
from typing import List, Tuple
from copy import copy


class Performance:
    def __init__(self, song_library_path: str, gesture_library_path: str, chunk_size=256, sample_rate=44100):
        self.song_lib_path = song_library_path
        self.gesture_lib_path = gesture_library_path
        self.chunk_size = chunk_size
        self.fs = sample_rate

        self.gesture_library = {}
        self.gestures = []
        self.load_gesture_library()

        self.audio_processor = AudioProcessor(chunk_size=self.chunk_size,
                                              sample_rate=sample_rate,
                                              audio_callback=self.callback)
        self.shimi = Shimi(LIMITS)
        self.udp = NetworkHandler(UDP_PORT, self.network_callback, timeout_sec=0.25)
        self.gesture_idx = 0
        self.play_idx = 0

        self.song = None

        self.perform_thread = threading.Thread(target=self.perform)
        signal.signal(signal.SIGINT, self.sig_handle)
        self.shimi.start()
        self.udp.start()

    def __del__(self):
        self.terminate()

    def load_gesture_library(self):
        for p in os.listdir(self.gesture_lib_path):
            path = os.path.join(self.gesture_lib_path, p)
            if os.path.isdir(path):
                temp = []
                for f in os.listdir(path):
                    fpath = os.path.join(path, f)
                    temp.append(self.load_gesture(fpath))
                self.gesture_library[Genre(p)] = temp

    def sig_handle(self, num, frame):
        self.terminate()

    def terminate(self):
        self.audio_processor.terminate()
        self.udp.terminate()
        self.shimi.terminate()

    def beats2sec(self, beats):
        return beats * (60.0 / self.song.tempo)

    def sec2beats(self, duration):
        return duration * self.song.tempo / 60.0

    @staticmethod
    def load_gesture(gesture_file: str):
        # DS: [motor id, start beat absolute, position (0, 1), length in beats]
        # Convert float values to int. beats -> samples, pos (0, 1) -> (0, 100)

        raw_data = np.loadtxt(gesture_file, delimiter=',')

        # Sort gestures in terms of their start times
        g = raw_data[raw_data[:, 1].argsort()]

        gestures = []
        for i, line in enumerate(g):
            gestures.append(Command(dxl_id=int(line[0]) - 1,
                                    angle=line[2],
                                    start_beat=line[1],
                                    duration=line[3]))

        return gestures

    def compose_gestures(self):
        segments = self.song.segments
        song_gesture = []
        offset = 0
        for i in range(1, len(segments)):

            # left and right boundaries
            l, r = self.sec2beats(segments[i - 1]), self.sec2beats(segments[i])
            seg_len = r - l

            # choose a random gesture
            gestures = self.gesture_library[self.song.genre]
            idx = np.random.randint(0, len(gestures), dtype=int)
            g: List[Command] = gestures[idx]
            g_dur = g[-1].start_beat + g[-1].duration
            num_loops = int(seg_len // g_dur)
            loop_dur = num_loops * g_dur
            residual_dur = round(seg_len - loop_dur)

            # loop / cut this gesture to fill this boundary
            seg_gesture: List[Command] = []

            # loop for num loops
            for j in range(num_loops):
                for c in g:
                    c = copy(c)
                    c.start_beat += offset
                    seg_gesture.append(c)
                offset += g_dur

            # handle residual duration
            cumsum_dur = 0
            for c in g:
                cumsum_dur += c.start_beat + c.duration
                if cumsum_dur > residual_dur:
                    break
                c = copy(c)
                c.start_beat += offset
                seg_gesture.append(c)

            offset = round(seg_len)
            song_gesture.extend(seg_gesture)

        return song_gesture

    def prepare(self, song: Song = None):
        if song:
            self.song = song

        if not self.song:
            return

        self.gesture_idx = 0
        self.play_idx = 0

        g = self.load_gesture("test.csv")
        self.gestures = self.compose_gestures()

    def perform(self, delay_ms=0):
        self.audio_processor.play(self.song.audio_path, delay_ms=delay_ms)
        self.stop()

    def stop(self):
        self.audio_processor.stop()
        if self.perform_thread.is_alive():
            self.perform_thread.join()
        self.shimi.stop()

    def callback(self, data: np.ndarray):
        # Haptic vibrations
        audio = np.mean(data, axis=1)
        data[:, 0] = audio
        data[:, 1] = Util.biquad_lpf(audio, fc=200, fs=self.fs) * 2

        # Motor actuation
        l = self.play_idx * self.chunk_size / self.fs
        r = (self.play_idx + 1) * self.chunk_size / self.fs

        if self.gesture_idx < len(self.gestures):
            cmd: Command = self.gestures[self.gesture_idx]

            # Add all the commands within this frame to the queue
            while l <= self.beats2sec(cmd.start_beat) < r:
                cmd.duration = self.beats2sec(cmd.duration)
                self.shimi.append_command(cmd)
                self.gesture_idx += 1
                if self.gesture_idx >= len(self.gestures):
                    break
                cmd = self.gestures[self.gesture_idx]

        self.play_idx += 1
        return data

    def network_callback(self, command: NetworkCommand, data):
        if command == NetworkCommand.START:
            if self.perform_thread.is_alive():
                print("Performance in progress. New performance cannot be accepted yet...")
            else:
                genre, song_name = data
                self.prepare(Song(self.song_lib_path, Genre(genre), song_name, self.fs))
                self.perform_thread.start()
        elif command == NetworkCommand.STOP:
            self.stop()
