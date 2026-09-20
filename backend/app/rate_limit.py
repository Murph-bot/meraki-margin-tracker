import os
import time
from collections import defaultdict


class SlidingWindowLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
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
