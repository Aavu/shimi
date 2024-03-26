import random

import numpy as np
import os
import signal
from shimi import Shimi, Command
from definitions import *
from audioProcessor import AudioProcessor
from networkHandler import NetworkCommand, NetworkHandler, Packet
from util import Util
from song import Song
from typing import List, Tuple, Optional
from copy import copy
from exceptions import *


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
                                              audio_callback=self.callback,
                                              complete_callback=self.song_complete_callback)
        self.shimi = Shimi(LIMITS)
        self.udp = NetworkHandler(UDP_PORT, self.network_callback, timeout_sec=0.25)
        self.gesture_idx = 0
        self.play_idx = 0
        self.paused = False

        self.song: Optional[Song] = None

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

    def join(self):
        self.audio_processor.stop()
        self.udp.join()
        self.shimi.join()

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
        song_gesture = []
        offset = 0
        last_idx = -1

        # print(f"segments: {self.song.segments}")
        for i in range(1, len(self.song.segments)):

            # left and right boundaries
            l, r = self.sec2beats(self.song.segments[i - 1]), self.sec2beats(self.song.segments[i])
            seg_len = r - l

            # choose a random gesture
            gestures = self.gesture_library[self.song.genre]

            # choose a random index (non-repeating) for gesture
            idx = random.choice([ii for ii in range(len(gestures)) if ii != last_idx])
            last_idx = idx

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

            offset += residual_dur

            song_gesture.extend(seg_gesture)

        return song_gesture

    def prepare(self, song: Song = None):
        if song:
            self.song = song

        if not self.song:
            return

        self.gesture_idx = 0
        self.play_idx = 0

        # g = self.load_gesture("test.csv")
        self.gestures = self.compose_gestures()

    def stop(self):
        self.audio_processor.stop()
        self.shimi.stop(reset_positions=True)
        if self.song:
            self.song.reset_lyric_idx()
        self.paused = False

    def pause(self):
        try:
            self.shimi.stop(reset_positions=True)
        except FastCommandException:
            pass

        self.audio_processor.pause()
        self.paused = True

    def pop_cmd(self) -> Command:
        if self.gesture_idx < len(self.gestures):
            cmd: Command = self.gestures[self.gesture_idx]
            cmd.duration = self.beats2sec(cmd.duration)
            cmd.start_beat = self.beats2sec(cmd.start_beat)
            self.gesture_idx += 1
            return cmd
        return Command()    # return dummy command

    def callback(self, data: np.ndarray):
        # Haptic vibrations
        audio = np.mean(data, axis=1)
        data[:, 0] = audio
        data[:, 1] = Util.biquad_lpf(audio, fc=100, fs=self.fs) * 2

        # Motor actuation
        l = self.play_idx * self.chunk_size / self.fs
        r = (self.play_idx + 1) * self.chunk_size / self.fs

        lrc: List[dict[int, str]] = self.song.get_lyrics_between(l, r, num_future=2)
        for line in lrc:
            self.udp.queue_to_send(line)

        # Add all the commands within this frame to the queue
        cmd = self.pop_cmd()
        w = cmd.start_beat - cmd.duration if cmd.dxl_id == 4 else cmd.start_beat
        while cmd.is_valid and l <= w < r:
            self.shimi.append_command(cmd)
            cmd = self.pop_cmd()
            w = cmd.start_beat - cmd.duration if cmd.dxl_id == 4 else cmd.start_beat

        self.play_idx += 1
        return data

    def song_complete_callback(self):
        self.shimi.stop(reset_positions=True)

    def network_callback(self, data: Packet):
        if data.command == NetworkCommand.START:
            if not self.paused or (self.song and self.song.id != data.song):
                self.stop()
                self.prepare(Song(self.song_lib_path, Genre(data.genre), data.song, self.fs))
                self.paused = False
            self.audio_processor.play(self.song.audio_path, delay_ms=0, block=False)
        elif data.command == NetworkCommand.STOP:
            self.stop()
        elif data.command == NetworkCommand.PAUSE:
            self.pause()
