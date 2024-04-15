import json
import pylrc
from pylrc.classes import LyricLine
from typing import List, Tuple, Optional, NamedTuple
import os
from definitions import *


class Song:
    class Segment(NamedTuple):
        start: float
        pace: float

    def __init__(self, library_root_path: str, genre: Genre, song_name, sample_rate=44100):
        self.library_path = library_root_path
        self._genre = genre
        self._song_name = song_name
        self.audio_path = os.path.join(library_root_path, genre.value, song_name + ".wav")
        self.meta_path = os.path.join(library_root_path, genre.value, song_name + ".json")
        self.lyrics_path = os.path.join(library_root_path, genre.value, song_name + ".lrc")

        self._lyrics: List[LyricLine] = []
        self._segments = []
        self.bpm = 120
        self.fs = sample_rate
        self.start = 0
        self.lrc_idx = 0

        self.parse_json()
        self.load_lyrics()

    @property
    def id(self):
        return self._song_name

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

    def reset_lyric_idx(self):
        self.lrc_idx = 0

    def get_lyrics_between(self, min_sec: float, max_sec: float, num_future: int = 2) -> List[dict[int, str]]:
        """
        returns List because there may be multiple lyric lines in the timeframe
        :param min_sec: minimum time stamp
        :param max_sec: maximum time stamp
        :param num_future: Number of future lyrics to return
        :return: list of dicts each containing the lyrics and futures with keys 0, 1, 2, ...
        """
        lrc = []

        # Move lrc pointer to the minimum time since we don't need anything before this point in time
        while self.lrc_idx < len(self._lyrics) and self._lyrics[self.lrc_idx].time < min_sec:
            self.lrc_idx += 1

        while self.lrc_idx < len(self._lyrics) and self._lyrics[self.lrc_idx].time < max_sec:
            tmp = {0: self._lyrics[self.lrc_idx].text}
            for i in range(1, num_future + 1):
                tmp[i] = self._lyrics[self.lrc_idx + i].text if self.lrc_idx + i < len(self._lyrics) else ""

            lrc.append(tmp)
            self.lrc_idx += 1
        return lrc

    def parse_json(self):
        with open(self.meta_path) as f:
            data = json.load(f)

        self._segments = self.parse_segmentation(data["segmentation"])
        self.bpm = data["tempo"]
        self.start = data["start"]

    @staticmethod
    def parse_segmentation(data: List[Tuple[float, float]]):
        segments: List[Song.Segment] = []
        for s, p in data:
            segments.append(Song.Segment(s, p))
        return segments

    def load_lyrics(self):
        with open(self.lyrics_path) as f:
            self._lyrics = pylrc.parse(f.read())
