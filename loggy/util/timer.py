"""
File: timer.py

Description: Util timer for tracking duration

@author Derek Garcia
"""
import time

ONE_HOUR = 3600
ONE_MINUTE = 60


class Timer:
    """
    Timer
    """

    def __init__(self, start: bool = True):
        """
        Create new timer

        :param start: Start the timer when created (Default: True)
        """
        self._start_time = time.time() if start else None
        self._end_time = None

    def start(self) -> None:
        """
        Start the timer
        """
        self._start_time = time.time()

    def stop(self) -> None:
        """
        Stop the timer
        """
        self._end_time = time.time()

    def get_count_per_second(self, count: int) -> float:
        """
        Calculate the count per second

        :param count: Number of items processed over the duration of the timer
        :raises RuntimeError: If the timer was never started or never stopped
        :return: Number of items processed per second
        """
        if self._start_time is None:
            raise RuntimeError("Timer was never started")
        if self._end_time is None:
            raise RuntimeError("Timer was never ended")

        duration = self._end_time - self._start_time
        # guard against dived by zero
        return count / duration if duration else 0.0

    def format_time(self, end_timer: bool = True) -> str:
        """
        Format elapsed seconds into hh:mm:ss string

        :param end_timer: End the timer (Default: True)
        :return: hours:minutes:seconds
        """
        if end_timer:
            self.stop()
        return format_time((self._end_time if self._end_time is not None else time.time()) - self._start_time)


def format_time(elapsed_seconds: float) -> str:
    """
    Format elapsed seconds into hh:mm:ss string

    :param elapsed_seconds: Elapsed time in seconds
    :return: hours:minutes:seconds
    """
    hours, remainder = divmod(int(elapsed_seconds), ONE_HOUR)
    minutes, seconds = divmod(remainder, ONE_MINUTE)
    return f"{hours:02}:{minutes:02}:{seconds:02}"
