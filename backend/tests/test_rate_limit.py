from unittest.mock import MagicMock, patch
from app.rate_limit import SlidingWindowLimiter


def test_sliding_window_allows_until_threshold():
    limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60)
    assert limiter.allow("login:a@example.com") is True
    assert limiter.allow("login:a@example.com") is True
    assert limiter.allow("login:a@example.com") is False


def test_sliding_window_is_per_key():
    limiter = SlidingWindowLimiter(max_attempts=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False
