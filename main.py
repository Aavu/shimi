"""
Author: Raghavasimhan Sankaranarayanan
Date created: 03/03/24
"""
from performance import Performance

if __name__ == '__main__':
    p = Performance(song_library_path="songs", gesture_library_path="gestures", chunk_size=1024, sample_rate=48000)
