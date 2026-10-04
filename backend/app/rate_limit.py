import os
import time
from collections import defaultdict

from fastapi import Request


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
auth_ip_limiter = SlidingWindowLimiter(max_attempts=50, window_seconds=900)


def get_client_ip(request: Request) -> str:
    """Return the client IP to key rate limits on.

    Railway's edge proxy overwrites X-Real-IP with the actual client address
    before forwarding the request, so that header is trustworthy here. We do
    not use X-Forwarded-For: on Railway its rightmost hop is the internal
    proxy hop (not the client), which would collapse the per-IP limiter into
    a single shared bucket for every user. Fall back to the socket peer when
    no header is present (e.g. local/dev requests not routed through Railway).
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    return request.client.host if request.client else ""


def auth_allowed(request: Request, prefix: str, email: str) -> bool:
    if os.environ.get("TESTING") == "1":
        return True
    ip = get_client_ip(request)
    if not auth_ip_limiter.allow(f"ip:{ip}"):
        return False
    return auth_limiter.allow(f"{prefix}:{ip}:{email}")
