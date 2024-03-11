import socket
import threading
from enum import IntEnum
import json
from typing import NamedTuple


class NetworkCommand(IntEnum):
    STOP = 0
    START = 1
    PAUSE = 2


class Packet(NamedTuple):
    command: NetworkCommand
    genre: str = ""
    song: str = ""

    def __repr__(self):
        return f"cmd: {self.command.name} \t genre: {self.genre} \t song: {self.song}"


class NetworkHandler:
    RECV_BUFFER = 128

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

    @staticmethod
    def parse_packet(packet: bytes):
        data: dict = json.loads(packet.decode())
        return Packet(NetworkCommand(data["cmd"]), data.get("genre"), data.get("song"))

    def recv_handler(self):
        while self.is_running:
            data = None
            try:
                data, addr = self.sock.recvfrom(NetworkHandler.RECV_BUFFER)
            except socket.timeout:
                continue

            data = self.parse_packet(data)
            if self.callback:
                self.callback(data)
