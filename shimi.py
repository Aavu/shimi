import copy
import queue
import time

import dynamixel_sdk as dxl
from definitions import *
from exceptions import *
from typing import List, Tuple
from motor import Motor
from threading import Thread, Condition, Lock
from dataclasses import dataclass


@dataclass
class Command:
    dxl_id: int = -1
    angle: float = 0
    start_beat: float = 0
    duration: float = 0

    @property
    def is_valid(self):
        return self.dxl_id >= 0 and self.duration > 0

    def __repr__(self):
        return f"id: {self.dxl_id} \t angle: {self.angle} \t start: {self.start_beat} \t period: {self.duration:.3f}sec"


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
        self.mutex = Lock()

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
        self.join()
        if self.port and self.port.is_open:
            self.port.closePort()

    def start(self):
        """
        Enable motors and start the queue thread
        :return:
        """
        for i, m in enumerate(self.motors):
            m.enable(wait=i == len(self.motors) - 1)
        self.is_running = True
        self.thread.start()

    def join(self):
        self.is_running = False
        self.stop()

        if self.thread.is_alive():
            self.thread.join()

    def stop(self, reset_positions=True):
        """
        Reset the queue. If reset_positions, reset the robot to initial positions.
        Note: This is for the thread. It will not disable motors.
        :param reset_positions: Whether the robot should go home (initial positions)
        :return: None
        """
        self.cmd_queue = queue.Queue()
        for i, m in enumerate(self.motors):
            m.reset_position(wait=i == len(self.motors) - 1)

    def append_command(self, command: Command):
        with self.cv:
            with self.mutex:
                self.cmd_queue.put_nowait(command)
                self.cv.notifyAll()

    def thread_handler(self):
        i = 0
        while self.is_running:
            with self.cv:
                self.cv.wait_for(lambda: self.cmd_queue.qsize() > 0 or not self.is_running, timeout=0.25)
                if not self.is_running:
                    break

                # There can be spurious awake. Use try catch to eliminate null
                with self.mutex:
                    try:
                        cmd: Command = copy.copy(self.cmd_queue.get_nowait())
                    except queue.Empty:
                        continue
                    self.cmd_queue.task_done()

            if not cmd.is_valid:
                continue

            # We don't need to worry about time here since the commands are appended at the time it needs to be executed
            print(i, cmd)
            i += 1
            self.motors[cmd.dxl_id].rotate(cmd.angle, cmd.duration, is_percent=True)
