import time
from collections.abc import Callable


class SlidingWindowRateLimiter:
    def __init__(
        self,
        window_seconds: float,
        max_messages: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window_seconds = window_seconds
        self._max_messages = max_messages
        self._clock = clock
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        now = self._clock()

        self._timestamps = [
            timestamp
            for timestamp in self._timestamps
            if timestamp > now - self._window_seconds
        ]

        if len(self._timestamps) >= self._max_messages:
            return False

        self._timestamps.append(now)
        return True
