import time


def getUptime(
    start_time: time,
) -> time:
    return time.time() - start_time
