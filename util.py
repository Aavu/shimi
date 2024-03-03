import numpy as np
from enum import IntEnum


class FilterType(IntEnum):
    LOW_PASS = 0
    HIGH_PASS = 1
    BAND_PASS = 2
    NOTCH = 3
    PEAK = 4
    LOW_SHELF = 5
    HIGH_SHELF = 6


class Util:
    @staticmethod
    def zero_lpf(x: np.ndarray, alpha):
        y = x.copy()
        for i in range(1, len(x)):
            y[i] = (alpha * y[i - 1]) + ((1 - alpha) * y[i])

        for i in range(len(x) - 2, -1, -1):
            y[i] = (alpha * y[i + 1]) + ((1 - alpha) * y[i])
        return y

    @staticmethod
    def get_biquad_coeff(filter_type: FilterType, fc, fs, Q, gain):
        a0, a1, a2, b1, b2 = 0, 0, 0, 0, 0
        V = np.power(10, np.abs(gain) / 20)
        K = np.tan(np.pi * fc / fs)
        if filter_type == FilterType.LOW_PASS:
            norm = 1 / (1 + K / Q + K * K)
            a0 = K * K * norm
            a1 = 2 * a0
            a2 = a0
            b1 = 2 * (K * K - 1) * norm
            b2 = (1 - K / Q + K * K) * norm

        elif filter_type == FilterType.HIGH_PASS:
            norm = 1 / (1 + K / Q + K * K)
            a0 = 1 * norm
            a1 = -2 * a0
            a2 = a0
            b1 = 2 * (K * K - 1) * norm
            b2 = (1 - K / Q + K * K) * norm

        elif filter_type == FilterType.BAND_PASS:
            norm = 1 / (1 + K / Q + K * K)
            a0 = K / Q * norm
            a1 = 0
            a2 = -a0
            b1 = 2 * (K * K - 1) * norm
            b2 = (1 - K / Q + K * K) * norm

        elif filter_type == FilterType.NOTCH:
            norm = 1 / (1 + K / Q + K * K)
            a0 = (1 + K * K) * norm
            a1 = 2 * (K * K - 1) * norm
            a2 = a0
            b1 = a1
            b2 = (1 - K / Q + K * K) * norm

        elif filter_type == FilterType.PEAK:
            if gain >= 0:  # boost
                norm = 1 / (1 + 1 / Q * K + K * K)
                a0 = (1 + V / Q * K + K * K) * norm
                a1 = 2 * (K * K - 1) * norm
                a2 = (1 - V / Q * K + K * K) * norm
                b1 = a1
                b2 = (1 - 1 / Q * K + K * K) * norm

            else:  # cut
                norm = 1 / (1 + V / Q * K + K * K)
                a0 = (1 + 1 / Q * K + K * K) * norm
                a1 = 2 * (K * K - 1) * norm
                a2 = (1 - 1 / Q * K + K * K) * norm
                b1 = a1
                b2 = (1 - V / Q * K + K * K) * norm

        elif filter_type == FilterType.LOW_SHELF:
            if gain >= 0:  # boost
                norm = 1 / (1 + np.SQRT2 * K + K * K)
                a0 = (1 + np.sqrt(2 * V) * K + V * K * K) * norm
                a1 = 2 * (V * K * K - 1) * norm
                a2 = (1 - np.sqrt(2 * V) * K + V * K * K) * norm
                b1 = 2 * (K * K - 1) * norm
                b2 = (1 - np.sqrt(2) * K + K * K) * norm

            else:  # cut
                norm = 1 / (1 + np.sqrt(2 * V) * K + V * K * K)
                a0 = (1 + np.sqrt(2) * K + K * K) * norm
                a1 = 2 * (K * K - 1) * norm
                a2 = (1 - np.sqrt(2) * K + K * K) * norm
                b1 = 2 * (V * K * K - 1) * norm
                b2 = (1 - np.sqrt(2 * V) * K + V * K * K) * norm

        elif filter_type == FilterType.HIGH_SHELF:
            if gain >= 0:  # boost
                norm = 1 / (1 + np.sqrt(2) * K + K * K)
                a0 = (V + np.sqrt(2 * V) * K + K * K) * norm
                a1 = 2 * (K * K - V) * norm
                a2 = (V - np.sqrt(2 * V) * K + K * K) * norm
                b1 = 2 * (K * K - 1) * norm
                b2 = (1 - np.sqrt(2) * K + K * K) * norm

            else:  # cut
                norm = 1 / (V + np.sqrt(2 * V) * K + K * K)
                a0 = (1 + np.sqrt(2) * K + K * K) * norm
                a1 = 2 * (K * K - 1) * norm
                a2 = (1 - np.sqrt(2) * K + K * K) * norm
                b1 = 2 * (K * K - V) * norm
                b2 = (V - np.sqrt(2 * V) * K + K * K) * norm
        else:
            print("Error: Unknown Filter type")
        return a0, a1, a2, b1, b2

    # refer: https://arachnoid.com/BiQuadDesigner/index.html
    @staticmethod
    def biquad_lpf(x: np.ndarray, fc, fs, Q=0.707, gain=1):
        b0, b1, b2, a1, a2 = Util.get_biquad_coeff(FilterType.LOW_PASS, fc, fs, Q, gain)
        x1, x2, y1, y2 = 0, 0, 0, 0

        def step(_x, _x1, _x2, _y1, _y2):
            _y = b0 * _x + b1 * _x1 + b2 * _x2 - a1 * _y1 - a2 * _y2
            return _y

        y = x.copy()
        for i in range(len(x)):
            y[i] = step(x[i], x1, x2, y1, y2)
            x2 = x1
            x1 = x[i]
            y2 = y1
            y1 = y[i]
        return y
