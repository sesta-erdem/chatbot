import pytest

from app.services.rate_limit import RateLimiter, RateLimitExceeded


def test_passes_under_max():
    limiter = RateLimiter(window=10.0, max_events=5)
    for _ in range(5):
        limiter.check("user-1")  # 5 kez geçmeli


def test_raises_on_exceed():
    limiter = RateLimiter(window=10.0, max_events=5)
    for _ in range(5):
        limiter.check("user-1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("user-1")


def test_keys_are_independent():
    """İki farklı kullanıcı birbirinin limitini etkilemez."""
    limiter = RateLimiter(window=10.0, max_events=5)
    for _ in range(5):
        limiter.check("user-1")
    # user-2 hâlâ özgür
    limiter.check("user-2")


def test_resets_after_window():
    limiter = RateLimiter(window=10.0, max_events=5)
    for _ in range(5):
        limiter.check("user-1")
    # zamanı sahte olarak pencere dışına it
    limiter._events["user-1"] = [t - 11 for t in limiter._events["user-1"]]
    limiter.check("user-1")  # raise etmemeli
