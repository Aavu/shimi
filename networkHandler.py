import socket
import threading
from enum import IntEnum


class NetworkCommand(IntEnum):
    STOP = 0
    START = 1
    PREPARE = 2  # contains data payload -> [genre: <genre> song_name: <song_name>]


class NetworkHandler:
    def __init__(self, port, command_callback=None, timeout_sec=0.25):
        self.port = port
        self.callback = command_callback

        self.thread = threading.Thread(target=self.recv_handler)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.sock.settimeout(timeout_sec)

        self.is_running = False

    def __del__(self):
        self.terminate()

    def terminate(self):
        self.join()
        self.sock.close()

    def join(self):
        self.is_running = False
        if self.thread.is_alive():
            self.thread.join()

    def start(self):
        self.is_running = True
        self.thread.start()

    def recv_handler(self):
        while self.is_running:
            data = None
            try:
                data, addr = self.sock.recvfrom(1)
            except socket.timeout:
                continue

            data = int.from_bytes(data, "little")
            if self.callback:
                self.callback(NetworkCommand(data))
