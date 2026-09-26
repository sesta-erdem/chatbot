# Cleanup summary

This cleanup keeps the existing architecture and D6 behavior while making the WebSocket handler easier to read.

## Main changes

- `core/metrics.py`
  - Added `ConnectionMetrics` to own active-connection and connection-duration bookkeeping.
  - Added `GenerationMetrics` to own request/success/error/timeout/latency bookkeeping.
  - Added provider error categories: `unavailable`, `rate_limit`, `request`, `unknown`.
  - Total latency is now recorded for successful, timeout, and provider-error attempts.

- `api/websocket.py`
  - Removed direct imports of individual Prometheus metric objects.
  - Consolidated provider exception handling into one `except ProviderError` block.
  - Moved repeated text validation decisions into `_validate_user_text()`.
  - Kept WebSocket transport responsibilities visible: accept, receive, validate, rate-limit, stream chunks, send done/error, disconnect.

- `main.py`
  - Cleaned import ordering.
  - Added shutdown logs around PostgreSQL and Gemini client cleanup.

- `providers/gemini.py`
  - Existing AFC disable configuration is retained.

## Local environment

The returned ZIP intentionally does not contain `.env`. Copy your existing `.env` into the project root before running it. `.env.example` is safe to use as a template.
