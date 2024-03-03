from enum import IntEnum
from typing import NamedTuple

SIMULATE = True

PORT_NAME = "USB0"
BAUD_RATE = 57600
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
    LIMIT(0, ENCODER_RESOLUTION // 2),
    LIMIT(0, ENCODER_RESOLUTION // 2),
    LIMIT(0, ENCODER_RESOLUTION // 2),
    LIMIT(0, ENCODER_RESOLUTION // 2),
    LIMIT(0, ENCODER_RESOLUTION // 2),
]


class PARAM_BYTE_LENGTH_MAP(NamedTuple):
    POSITION = 2
    VELOCITY = 2
