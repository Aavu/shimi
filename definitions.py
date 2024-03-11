from enum import IntEnum, Enum
from typing import NamedTuple

SIMULATE = True

OUTPUT_AUDIO_DEVICE = "LG HDR 4K"   # "USB Audio Device"

PORT_NAME = "/dev/tty.usbserial-FT62AO7Z"
BAUD_RATE = 1000000
ENCODER_RESOLUTION = 4096
ACK_TIMEOUT_MS = 100

UDP_PORT = 8888


class ADDR(IntEnum):
    TORQUE_ENABLE = 24
    GOAL_POSITION = 30
    GOAL_VELOCITY = 32
    PRESENT_POSITION = 36


class LIMIT:
    MIN = 0
    MAX = ENCODER_RESOLUTION

    def __init__(self, minimum=0, maximum=ENCODER_RESOLUTION):
        self.MIN = minimum
        self.MAX = maximum


LIMITS = [
    LIMIT(1929, 2214),
    LIMIT(1400, 2210),
    LIMIT(1730, 2175),
    LIMIT(0, ENCODER_RESOLUTION - 1),
    LIMIT(2110, 2300),
]

INITIAL_POSITIONS = [2214, 1805, 2175, 0, 2110]


class PARAM_BYTE_LENGTH_MAP(NamedTuple):
    POSITION = 2
    VELOCITY = 2


class Genre(Enum):
    POP = "pop"
    EDM = "edm"
    FUNK = "funk"
    ROCK = "rock"
