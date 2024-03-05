import socket
import time
from enum import IntEnum
import json


PORT = 8888
IP = "127.0.0.1"


class NetworkCommand(IntEnum):
    STOP = 0
    START = 1  # contains data payload -> [<genre> <song_name>]


def serialize(cmd: NetworkCommand, genre: str or None = None, song: str or None = None):
    return json.dumps({"cmd": cmd, "genre": genre, "song": song}).encode()


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.sendto(serialize(NetworkCommand.START, genre="edm", song="drums_120"), (IP, PORT))
    time.sleep(5)
    sock.sendto(serialize(NetworkCommand.START, genre="edm", song="drums_120"), (IP, PORT))
    time.sleep(10)
    sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))
