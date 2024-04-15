"""
Author: Raghavasimhan Sankaranarayanan
Date created: 03/03/24
"""

import socket
from threading import Thread, Condition, Lock
from enum import IntEnum
import json
from typing import NamedTuple
import queue


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

        self.recv_thread = Thread(target=self.recv_handler)
        self.send_thread = Thread(target=self.send_handler)
        self._cv = Condition()
        self._queue = queue.Queue()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.sock.settimeout(timeout_sec)

        self.remote_addr = None

        self.is_running = False

    def __del__(self):
        self.terminate()

    def terminate(self):
        self.join()
        self.sock.close()

    def join(self):
        self.is_running = False
        if self.recv_thread.is_alive():
            self.recv_thread.join()
        if self.send_thread.is_alive():
            self.send_thread.join()

    def start(self):
        self.is_running = True
        self.recv_thread.start()
        self.send_thread.start()

    @staticmethod
    def parse_packet(packet: bytes):
        data: dict = json.loads(packet.decode())
        return Packet(NetworkCommand(data["cmd"]), data.get("genre"), data.get("song"))

    def queue_to_send(self, data: dict):
        with self._cv:
            self._queue.put_nowait(data)
            self._cv.notifyAll()

    def send(self, packet):
        if self.remote_addr:
            self.sock.sendto(packet, (self.remote_addr[0], self.port + 1))

    def recv_handler(self):
        while self.is_running:
            try:
                data, self.remote_addr = self.sock.recvfrom(NetworkHandler.RECV_BUFFER)
            except socket.timeout:
                continue

            data = self.parse_packet(data)
            if self.callback:
                self.callback(data)

    def send_handler(self):
        while self.is_running:
            with self._cv:
                self._cv.wait_for(lambda: self._queue.qsize() > 0 or not self.is_running, timeout=0.25)
                if not self.is_running:
                    break
                try:
                    data = json.dumps(self._queue.get_nowait()).encode()
                except queue.Empty:
                    continue
                self._queue.task_done()

            self.send(data)
