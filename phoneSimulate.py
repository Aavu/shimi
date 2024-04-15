import socket
import threading
import time
from enum import IntEnum
import json
import signal

PORT = 8888
RECV_PORT = PORT + 1
IP = "127.0.0.1"    # "10.42.0.1"    # "127.0.0.1"

RECV_BUFFER = 1024


class NetworkCommand(IntEnum):
    STOP = 0
    START = 1  # contains data payload -> [<genre> <song_name>]
    PAUSE = 2


def serialize(cmd: NetworkCommand, genre: str or None = None, song: str or None = None):
    return json.dumps({"cmd": cmd, "genre": genre, "song": song}).encode()


is_running = True


def recv_handler(s):
    print("Listening for Lyrics...")
    while is_running:
        try:
            data, remote_addr = s.recvfrom(RECV_BUFFER)
        except socket.timeout:
            continue
        data = json.loads(data.decode())
        print(data['0'])


def sleep(sec: int):
    i = 0
    while is_running and i < sec:
        time.sleep(1)
        i += 1


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    thread = threading.Thread(target=recv_handler, args=(sock,))


    def terminate(signum=2, frame=None):
        global is_running, thread, sock
        sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))
        is_running = False
        if thread.is_alive():
            thread.join()
        sock.close()


    signal.signal(signal.SIGINT, terminate)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.25)
    sock.bind(("", RECV_PORT))
    thread.start()

    if is_running:
        sock.sendto(serialize(NetworkCommand.START, genre="funk", song="Get_lucky"), (IP, PORT))
        sleep(30)
    # if is_running:
    #     sock.sendto(serialize(NetworkCommand.PAUSE), (IP, PORT))
    #     sleep(2)
    # if is_running:
    #     sock.sendto(serialize(NetworkCommand.START, genre="edm", song="All_around_the_world"), (IP, PORT))
    #     sleep(5)
    # if is_running:
    #     sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))
    #     sleep(1)
    # if is_running:
    #     sock.sendto(serialize(NetworkCommand.START, genre="edm", song="All_around_the_world"), (IP, PORT))
    #     sleep(15)

    # if is_running:
    #     sock.sendto(serialize(NetworkCommand.STOP), (IP, PORT))

    terminate()
