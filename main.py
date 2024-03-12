import time

import numpy as np

from performance import Performance
from song import Song
from definitions import *
from shimi import Shimi, Command

robot = Shimi(LIMITS)


if __name__ == '__main__':
    # cmd = Command(1, 0, 0, 0.5)
    # robot.start()
    # time.sleep(2)
    # robot.append_command(cmd)
    # time.sleep(10)
    # robot.terminate()
    p = Performance(song_library_path="songs", gesture_library_path="gestures", chunk_size=1024, sample_rate=48000)
    # p.prepare(Song(p.song_lib_path, genre=Genre.EDM, song_name="Closer"))
    # p.perform(delay_ms=0)
