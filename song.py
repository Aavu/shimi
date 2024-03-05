import json
import os
import numpy as np
from definitions import *


class Song:
    def __init__(self, library_root_path: str, genre: Genre, song_name, sample_rate=44100):
        self.library_path = library_root_path
        self._genre = genre
        self._song_name = song_name
        self.audio_path = os.path.join(library_root_path, genre.value, song_name + ".wav")
        self.meta_path = os.path.join(library_root_path, genre.value, song_name + ".json")
        self._segments = []
        self.bpm = 120
        self.fs = sample_rate
        self.start = 0

        self.parse_json()

    @property
    def sample_rate(self):
        return self.fs

    @property
    def tempo(self):
        return self.bpm

    @property
    def start_time(self):
        return self.start

    @property
    def genre(self):
        return self._genre

    @property
    def segments(self):
        return self._segments

    def parse_json(self):
        with open(self.meta_path) as f:
            data = json.load(f)

        self._segments = np.array(data["segmentation"])
        self.bpm = data["tempo"]
        self.start = data["start"]
