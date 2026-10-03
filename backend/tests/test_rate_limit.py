from starlette.requests import Request

from app.rate_limit import SlidingWindowLimiter, get_client_ip


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


def _make_request(ip="9.9.9.9", forwarded_for=None):
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "headers": headers,
        "client": (ip, 12345),
    }
    return Request(scope)


def test_get_client_ip_prefers_rightmost_forwarded_hop():
    # The leftmost hop is attacker-controlled (sent verbatim by the client);
    # only the rightmost hop, appended by our own trusted proxy, is safe to use.
    request = _make_request(ip="10.0.0.1", forwarded_for="203.0.113.7, 10.0.0.1")
    assert get_client_ip(request) == "10.0.0.1"


def test_get_client_ip_falls_back_to_socket_peer_without_header():
    request = _make_request(ip="203.0.113.7", forwarded_for=None)
    assert get_client_ip(request) == "203.0.113.7"


def test_auth_allowed_per_email_limit_is_scoped_per_ip(monkeypatch):
    import app.rate_limit as rl

    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setattr(rl, "auth_limiter", SlidingWindowLimiter(max_attempts=2, window_seconds=60))
    monkeypatch.setattr(rl, "auth_ip_limiter", SlidingWindowLimiter(max_attempts=1000, window_seconds=900))

    victim_from_attacker_ip = _make_request(ip="198.51.100.1")
    victim_from_own_ip = _make_request(ip="198.51.100.2")

    # An attacker hammering one email from their own IP should not be able to
    # lock the victim out when the victim logs in from a different IP.
    assert rl.auth_allowed(victim_from_attacker_ip, "login", "victim@example.com") is True
    assert rl.auth_allowed(victim_from_attacker_ip, "login", "victim@example.com") is True
    assert rl.auth_allowed(victim_from_attacker_ip, "login", "victim@example.com") is False

    assert rl.auth_allowed(victim_from_own_ip, "login", "victim@example.com") is True


def test_auth_allowed_enforces_per_ip_limit_across_many_emails(monkeypatch):
    import app.rate_limit as rl

    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setattr(rl, "auth_limiter", SlidingWindowLimiter(max_attempts=1000, window_seconds=60))
    monkeypatch.setattr(rl, "auth_ip_limiter", SlidingWindowLimiter(max_attempts=2, window_seconds=900))

    attacker = _make_request(ip="198.51.100.9")

    # Credential stuffing across many different emails from one client IP
    # must still get throttled, even though each email is fresh.
    assert rl.auth_allowed(attacker, "login", "a@example.com") is True
    assert rl.auth_allowed(attacker, "login", "b@example.com") is True
    assert rl.auth_allowed(attacker, "login", "c@example.com") is False
