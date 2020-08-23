import time
import numpy as np

class TimedService:
    """
    A simple class that implements a timer (to be called in a loop)

    """

    def __init__(self, frequency_hz, function, args=[]):
        """
        arguments:
            frequency_hz (float): timer frequency
            function (function): function to call
            args (list): arguments to supplied function

        """
        self.function = function
        self.args = args
        self.last_service = 0
        self.timeout = 1. / frequency_hz
        self._latency_size = 20
        self._timer_latency = np.zeros(self._latency_size)
        self._function_latency = np.zeros(self._latency_size)
        self.times_called = 0

    def service(self):
        """
        Check when the timer was last run, and call the user-supplied function
        if required

        """
        elapsed = time.time() - self.last_service

        if elapsed >= self.timeout:

            tstart = time.time()
            self.function(*self.args)

            self._function_latency[self.times_called % self._latency_size] = time.time() - tstart

            # Only latency after first call to avoid huge number
            if self.times_called > 0:
                self._timer_latency[self.times_called % self._latency_size] = elapsed

            self.times_called += 1
            self.last_service = time.time()

    def function_latency(self):
        """
        Return latency stats for this timer

        """
        times = self._function_latency[self._function_latency > 0]

        if len(times) == 0:
            return None

        return times

    def timer_latency(self):
        """
        Return latency stats for this timer

        """
        times = self._timer_latency[self._timer_latency > 0]

        if len(times) == 0:
            return None

        return times
