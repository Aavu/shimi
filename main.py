import signal
from shimi import Shimi
from performance import Performance
from definitions import *
import numpy as np
import signal


if __name__ == '__main__':
    p = Performance(chunk_size=256, sample_rate=44100)
    p.perform(audio_path="drums_120.wav", gesture_file="gestures/edm_1.csv", tempo=120)
