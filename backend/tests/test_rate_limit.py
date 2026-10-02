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


def test_expired_keys_are_evicted(monkeypatch):
    import app.rate_limit as rl

    clock = [1000.0]
    monkeypatch.setattr(rl.time, "monotonic", lambda: clock[0])
    limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
    for i in range(1000):
        limiter.allow(f"login:user{i}@example.com")
    clock[0] += 120
    limiter.allow("login:fresh@example.com")
    assert len(limiter._hits) == 1
