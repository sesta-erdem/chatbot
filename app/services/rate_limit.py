import time


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    """
    Anahtar-başına (kullanıcı id'si) kayan pencere hız sınırı.
    Tek worker (D8 kararı) olduğu için bellekte tutmak yeterli; çoğaltılırsa
    paylaşımlı bir store'a (Redis) taşınır.
    İki sekme açan aynı kullanıcı artık limiti ikiye katlayamaz (anahtar = user_id).
    """

    def __init__(self, window: float = 10.0, max_events: int = 5) -> None:
        self._window = window
        self._max = max_events
        self._events: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        events = [t for t in self._events.get(key, []) if t > now - self._window]
        if len(events) >= self._max:
            self._events[key] = events
            raise RateLimitExceeded(f"{key}: pencerede {len(events)} istek")
        events.append(now)
        self._events[key] = events
