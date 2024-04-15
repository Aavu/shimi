"""
Author: Raghavasimhan Sankaranarayanan
Date created: 03/03/24
"""

import math

import dynamixel_sdk as dxl
import numpy as np

from definitions import *
from exceptions import *
import time


class Motor:
    def __init__(self, port_handler: dxl.PortHandler, dxl_id: int,
                 motion_limit: LIMIT,
                 encoder_resolution: int = ENCODER_RESOLUTION,
                 moving_threshold: int = 20,
                 cmd_rate_ms: int = 50):
        self.port = port_handler
        self.id = dxl_id
        self.packet_handler = dxl.PacketHandler(protocol_version=1)
        self.LIMIT = motion_limit
        self.ENCODER_RESOLUTION = encoder_resolution
        self.MOVING_THRESHOLD = moving_threshold
        self.cmd_rate = cmd_rate_ms / 1000.0

        self.byte_length = {1, 2, 4}
        self.byte_map = PARAM_BYTE_LENGTH_MAP()

        self.last_cmd_time = time.time() - 10
        self.current_position = 0

    def __del__(self):
        self.reset()

    def reset(self, wait=False):
        self.enable(False, wait=wait)

    def in_range(self, value):
        return self.LIMIT.MIN <= value <= self.LIMIT.MAX

    def enable(self, enable=True, wait=False):
        self.write(ADDR.TORQUE_ENABLE, 1 if enable else 0, 1)

        if enable:
            self.current_position = self.read_position()
            self.move_to_position(INITIAL_POSITIONS[self.id], 1, wait=wait)

    def reset_position(self, wait=False):
        try:
            self.move_to_position(INITIAL_POSITIONS[self.id], 1, wait=wait)
        except FastCommandException:
            print("Warning: Fast Command")

    def rotate(self, value: float, duration: float, is_percent=False):
        """
        Rotate the motor with value either in radians or % of limit dictated by is_percent
        :param value: angle in radians or % of limit
        :param duration: Length of the trajectory
        :param is_percent: whether the value is angle or percent
        :return: None
        """
        # No need to check angle limit here since we check position limits before writing
        ticks = self.percent2ticks(value) if is_percent else self.angle2ticks(value, is_radian=True)

        try:
            self.move_to_position(ticks, duration)
        except FastCommandException:
            print("Fast command!")

    def ticks2angle(self, ticks: int):
        return (ticks * 1.0 / self.ENCODER_RESOLUTION) * (2 * math.pi)

    def percent2ticks(self, cent: float) -> int:
        return int(self.LIMIT.MIN + ((self.LIMIT.MAX - self.LIMIT.MIN) * cent))

    def angle2ticks(self, angle, is_radian=True) -> int:
        if not is_radian:
            angle = np.deg2rad(angle)
        return int((angle / (2 * math.pi)) * self.ENCODER_RESOLUTION)

    def get_rpm_ticks(self, target, duration):
        velocity = self.ticks2angle(abs(self.current_position - target)) / duration
        rpm = velocity * 60 / (2 * math.pi)
        return int(round(rpm / 0.114))  # refer: https://emanual.robotis.com/docs/en/dxl/mx/mx-28/#moving-speed

    def move_to_position(self, position: int, duration: float, wait=False):
        if not self.in_range(position):
            raise NotInRangeException

        if self.last_cmd_time and time.time() - self.last_cmd_time < self.cmd_rate:
            raise FastCommandException

        rpm_ticks = self.get_rpm_ticks(position, duration)

        if rpm_ticks >= 1024:
            print(f"rpm too high: {rpm_ticks}")
            rpm_ticks = min(rpm_ticks, 1023)

        # print(f"id: {self.id}, pos: {position}, dur: {duration}, rpm: {rpm_ticks}")
        try:
            self.write(ADDR.GOAL_VELOCITY, rpm_ticks, size=self.byte_map.VELOCITY)
            self.write(ADDR.GOAL_POSITION,
                       position,
                       size=self.byte_map.POSITION,
                       read_addr=ADDR.PRESENT_POSITION if wait else None)

            self.last_cmd_time = time.time()
            self.current_position = position
        except DxlCommError:
            print("Dynamixel Communication Error")

    def read_position(self):
        pos = self.read(ADDR.PRESENT_POSITION, size=self.byte_map.POSITION)
        self.current_position = pos
        return pos

    def read(self, addr: int, size: int):
        value = self.current_position
        if not SIMULATE:
            value, res, err = self.packet_handler.read2ByteTxRx(self.port, self.id + 1, addr)
            if res != dxl.COMM_SUCCESS or err != 0:
                print(res, err)
                raise DxlCommError
        return value

    def write(self, write_addr: int, data: int, size: int, read_addr: int or None = None):
        if size not in self.byte_length:
            raise IllegalSizeException

        if not SIMULATE:
            err = 0
            res = dxl.COMM_SUCCESS

            if size == 1:
                res, err = self.packet_handler.write1ByteTxRx(self.port, self.id + 1, write_addr, data)
            elif size == 2:
                res, err = self.packet_handler.write2ByteTxRx(self.port, self.id + 1, write_addr, data)
            elif size == 4:
                res, err = self.packet_handler.write4ByteTxRx(self.port, self.id + 1, write_addr, data)

            if res != dxl.COMM_SUCCESS or err != 0:
                raise DxlCommError

            if read_addr is not None:
                t = time.time()
                timeout = float("inf") if ACK_TIMEOUT_MS <= 0 else ACK_TIMEOUT_MS / 1000.0

                while time.time() - t < timeout:
                    ret_data, res, err = self.packet_handler.readTxRx(self.port, self.id, read_addr, size)
                    if res != dxl.COMM_SUCCESS or err != 0:
                        raise DxlCommError

                    if abs(data - ret_data[0]) < self.MOVING_THRESHOLD:
                        break

        else:
            time.sleep(0.005)
