import math


def decay(initial, rate_per_second, times_ms):
    return [initial * math.exp(-rate_per_second * t) for t in times_ms]
