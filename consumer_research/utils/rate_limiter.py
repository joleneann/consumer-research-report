"""Rate limiting for API calls."""

import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Token-bucket style rate limiter.

    Args:
        max_calls: Maximum number of calls allowed in the window.
        window_seconds: Time window in seconds.
    """

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    def wait(self) -> None:
        """Block until a call is allowed within the rate limit."""
        with self._lock:
            now = time.monotonic()
            # Remove timestamps outside the window
            while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_calls:
                sleep_until = self._timestamps[0] + self.window_seconds
                sleep_time = sleep_until - now
                if sleep_time > 0:
                    time.sleep(sleep_time)

            self._timestamps.append(time.monotonic())
