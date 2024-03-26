import time

import numpy as np

from performance import Performance
from song import Song
from definitions import *
from shimi import Shimi, Command

robot = Shimi(LIMITS)


if __name__ == '__main__':
    p = Performance(song_library_path="songs", gesture_library_path="gestures", chunk_size=1024, sample_rate=48000)
