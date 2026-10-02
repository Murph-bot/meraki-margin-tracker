import os
import time
from collections import defaultdict


class SlidingWindowLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._last_sweep = 0.0

    def _sweep(self, now: float) -> None:
        # Drop keys whose newest hit is outside the window so the dict does not
        # grow with every email ever tried.
        if now - self._last_sweep < self.window_seconds:
            return
        self._last_sweep = now
        window_start = now - self.window_seconds
        for key in [k for k, stamps in self._hits.items() if not stamps or stamps[-1] < window_start]:
            del self._hits[key]

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        self._sweep(now)
        window_start = now - self.window_seconds
        recent = [stamp for stamp in self._hits[key] if stamp >= window_start]
        if len(recent) >= self.max_attempts:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True


auth_limiter = SlidingWindowLimiter(max_attempts=20, window_seconds=60)


def auth_allowed(key: str) -> bool:
    if os.environ.get("TESTING") == "1":
        return True
    return auth_limiter.allow(key)
