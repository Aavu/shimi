import queue

import dynamixel_sdk as dxl
from definitions import *
from exceptions import *
from typing import List, Tuple
from motor import Motor
from threading import Thread, Condition
from dataclasses import dataclass


@dataclass
class Command:
    dxl_id: int = -1
    angle: float = 0
    start_time: float = 0
    duration: int = 0

    @property
    def is_valid(self):
        return self.dxl_id >= 0 and self.duration > 0

    def __repr__(self):
        return f"id: {self.dxl_id} \t angle: {self.angle} \t time: {self.start_time} \t period: {self.duration}"


class Shimi:
    def __init__(self, limits: List[LIMIT]):
        self.port = None
        if not SIMULATE:
            self.port = dxl.PortHandler(PORT_NAME)
            self.__init_port__()
        self.motors = [Motor(self.port, i, limits[i]) for i in range(len(limits))]

        self.is_running = False
        self.cmd_queue = queue.Queue()
        self.thread = Thread(target=self.thread_handler)
        self.cv = Condition()

    def __init_port__(self):
        if self.port.is_open:
            self.port.closePort()

        if self.port.openPort():
            print("Port opened successfully")
        else:
            raise DxlPortOpenError

        if self.port.setBaudRate(BAUD_RATE):
            print(f"Baud rate set to {BAUD_RATE}")
        else:
            raise DxlCommError

    def __del__(self):
        self.terminate()

    def terminate(self):
        self.is_running = False
        self.stop()
        if self.thread.is_alive():
            self.thread.join()

        for m in self.motors:
            m.reset()

        if self.port and self.port.is_open:
            self.port.closePort()

    def start(self):
        self.is_running = True
        self.thread.start()

    def stop(self):
        self.cmd_queue = queue.Queue()

    def append_command(self, command: Command):
        with self.cv:
            self.cmd_queue.put_nowait(command)
            self.cv.notifyAll()

    def thread_handler(self):
        while self.is_running:
            with self.cv:
                self.cv.wait_for(lambda: self.cmd_queue.qsize() > 0 or not self.is_running, timeout=0.25)
                if not self.is_running:
                    break

                # There can be spurious awake. Use try catch to eliminate null
                try:
                    cmd: Command = self.cmd_queue.get_nowait()
                except queue.Empty:
                    continue

            if not cmd.is_valid:
                continue

            # We don't need to worry about time here since the commands are appended at the time it needs to be executed
            print(cmd)
            self.motors[cmd.dxl_id].rotate(cmd.angle, cmd.duration, is_percent=True)