import math

import dynamixel_sdk as dxl
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
        self.packet_handler = dxl.PacketHandler(protocol_version=2)
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

    def reset(self):
        self.enable(False)

    def in_range(self, value):
        return self.LIMIT.MIN <= value <= self.LIMIT.MAX

    def enable(self, enable=True):
        self.write(ADDR.TORQUE_ENABLE, enable, 1)
        self.current_position = self.read(ADDR.PRESENT_POSITION, self.byte_map.POSITION)

    def rotate(self, value: float, duration: float, is_percent=False):
        """
        Rotate the motor with value either in radians or % of limit dictated by is_percent
        :param value: angle in radians or % of limit
        :param duration: Length of the trajectory
        :param is_percent: whether the value is angle or percent
        :return: None
        """
        # No need to check angle limit here since we check position limits before writing
        if is_percent:
            ticks = self.LIMIT.MIN + ((self.LIMIT.MAX - self.LIMIT.MIN) * value)
        else:
            ticks = (value / (2 * math.pi)) * self.ENCODER_RESOLUTION

        self.move_to_position(int(ticks), duration)

    def ticks2angle(self, ticks: int):
        return (ticks * 1.0 / self.ENCODER_RESOLUTION) * (2 * math.pi)

    def get_rpm_ticks(self, target, duration):
        velocity = self.ticks2angle(abs(self.current_position - target)) / duration
        rpm = velocity * 60 / (2 * math.pi)

        return int(round(rpm / 0.114))  # refer: https://emanual.robotis.com/docs/en/dxl/mx/mx-28/#moving-speed

    def move_to_position(self, position: int, duration: float):
        if not self.in_range(position):
            raise NotInRangeException

        if self.last_cmd_time and time.time() - self.last_cmd_time < self.cmd_rate:
            raise FastCommandException

        rpm_ticks = self.get_rpm_ticks(position, duration)

        if rpm_ticks >= 1024:
            raise NotInRangeException

        try:
            self.write(ADDR.GOAL_VELOCITY, rpm_ticks, size=self.byte_map.VELOCITY)
            self.write(ADDR.GOAL_POSITION,
                       position,
                       size=self.byte_map.POSITION,
                       read_addr=ADDR.PRESENT_POSITION)

            self.last_cmd_time = time.time()
            self.current_position = position
        except DxlCommError:
            print("Dynamixel Communication Error")

    def read(self, addr: int, size: int):
        value = 0
        if not SIMULATE:
            value, res, err = self.packet_handler.readTxRx(self.port, self.id, addr, size)
            if res != dxl.COMM_SUCCESS or err != 0:
                raise DxlCommError
        return value

    def write(self, write_addr: int, data: int, size: int, read_addr: int or None = None,
              timeout_ms: int or None = ACK_TIMEOUT_MS):
        if size not in self.byte_length:
            raise IllegalSizeException

        if timeout_ms < 0:
            timeout_ms = None

        if not SIMULATE:
            if read_addr is not None:
                res, err = self.packet_handler.writeTxRx(self.port, self.id, write_addr, size, data)
            else:
                res, err = self.packet_handler.writeTxOnly(self.port, self.id, write_addr, size, data)

            if res != dxl.COMM_SUCCESS or err != 0:
                raise DxlCommError

            if read_addr is not None:
                t = time.time()
                timeout = float("inf")
                if timeout_ms is not None:
                    timeout = timeout_ms / 1000.0

                while time.time() - t < timeout:
                    ret_data, res, err = self.packet_handler.readTxRx(self.port, self.id, read_addr, size)
                    if res != dxl.COMM_SUCCESS or err != 0:
                        raise DxlCommError

                    if abs(data - ret_data) < self.MOVING_THRESHOLD:
                        break
        else:
            time.sleep(0.001)
