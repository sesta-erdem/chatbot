import time

from prometheus_client import Counter, Gauge, Histogram


ACTIVE_CONNECTIONS = Gauge(
    "chat_active_connections",
    "Number of currently active WebSocket connections",
)

CONNECTION_DURATION = Histogram(
    "chat_connection_duration_seconds",
    "WebSocket connection duration in seconds",
)

REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total number of chat generation requests",
)

SUCCESS_TOTAL = Counter(
    "chat_success_total",
    "Total number of successful chat generations",
)

ERRORS_TOTAL = Counter(
    "chat_errors_total",
    "Total number of failed chat generations",
)

TIMEOUTS_TOTAL = Counter(
    "chat_timeouts_total",
    "Total number of timed out chat generations",
)

PROVIDER_ERRORS_TOTAL = Counter(
    "chat_provider_errors_total",
    "Total provider errors by category",
    ["category"],
)

FIRST_TOKEN_LATENCY = Histogram(
    "chat_first_token_latency_seconds",
    "Time from request start until first model chunk",
)

TOTAL_LATENCY = Histogram(
    "chat_total_latency_seconds",
    "Total chat generation duration for all attempts",
)


for _category in ("unavailable", "rate_limit", "request", "unknown"):
    PROVIDER_ERRORS_TOTAL.labels(category=_category)


class ConnectionMetrics:
    """Tracks metrics for one accepted WebSocket connection."""

    def __init__(self) -> None:
        self._started_at = time.perf_counter()
        self._finished = False
        ACTIVE_CONNECTIONS.inc()

    def finish(self) -> None:
        if self._finished:
            return

        self._finished = True
        ACTIVE_CONNECTIONS.dec()
        CONNECTION_DURATION.observe(
            time.perf_counter() - self._started_at
        )


class GenerationMetrics:
    """Tracks metrics for one chat generation attempt."""

    def __init__(self) -> None:
        self._started_at = time.perf_counter()
        self._first_token_recorded = False
        self._finished = False
        REQUESTS_TOTAL.inc()

    def record_first_token(self) -> None:
        if self._first_token_recorded:
            return

        self._first_token_recorded = True
        FIRST_TOKEN_LATENCY.observe(
            time.perf_counter() - self._started_at
        )

    def record_success(self) -> None:
        SUCCESS_TOTAL.inc()

    def record_timeout(self) -> None:
        ERRORS_TOTAL.inc()
        TIMEOUTS_TOTAL.inc()

    def record_provider_error(self, category: str) -> None:
        ERRORS_TOTAL.inc()
        PROVIDER_ERRORS_TOTAL.labels(category=category).inc()

    def finish(self) -> None:
        if self._finished:
            return

        self._finished = True
        TOTAL_LATENCY.observe(
            time.perf_counter() - self._started_at
        )
