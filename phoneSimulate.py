import socket
import time
from enum import IntEnum
import json


PORT = 8888
IP = "10.42.0.1"    # "127.0.0.1" # "192.168.0.101"


class NetworkCommand(IntEnum):
    STOP = 0
    START = 1  # contains data payload -> [<genre> <song_name>]
    PAUSE = 2


def serialize(cmd: NetworkCommand, genre: str or None = None, song: str or None = None):
    return json.dumps({"cmd": cmd, "genre": genre, "song": song}).encode()


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.sendto(serialize(NetworkCommand.START, genre="edm", song="Happier"), (IP, PORT))
    time.sleep(2)
    sock.sendto(serialize(NetworkCommand.PAUSE), (IP, PORT))
    time.sleep(2)
    sock.sendto(serialize(NetworkCommand.START, genre="edm", song="Happier"), (IP, PORT))
    time.sleep(2)
    # sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))
    # time.sleep(1)
    sock.sendto(serialize(NetworkCommand.START, genre="edm", song="All_around_the_world"), (IP, PORT))
    time.sleep(5)
    sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))
