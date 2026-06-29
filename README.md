# FastAPI + WebSocket + Gemini Chatbot

A real-time streaming chatbot built on **FastAPI**, **WebSocket**, and **Google Gemini**, with persistent conversation history in **PostgreSQL**. Token-authenticated, origin-checked, rate-limited, observable, tested, and containerized.

## Quickstart (Docker)

```bash
git clone <repo-url>
cd <repo>
cp .env.example .env        # fill in GEMINI_API_KEY and APP_ACCESS_TOKEN
docker compose up --build
```

This starts PostgreSQL, applies database migrations, and launches the app at <http://127.0.0.1:8000>. Open it, paste your access token, and chat. Reload the page — the bot remembers the conversation (history is restored from PostgreSQL).

## Run locally (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Start a local PostgreSQL and create a database, then set DATABASE_URL in .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pip install pytest pytest-asyncio httpx
pytest
```

Tests never call the real Gemini API or a real database — they use a `FakeProvider` and a `FakeRepository`, so they are fast and free.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | yes | — | Google Gemini API key |
| `APP_ACCESS_TOKEN` | yes | — | Legacy shared token (kept for config compatibility) |
| `JWT_SECRET` | yes | — | Secret for signing JWTs (min 16 chars) |
| `DATABASE_URL` | yes | — | Must use the async driver: `postgresql+asyncpg://...` |
| `ALLOWED_ORIGINS` | yes | — | JSON list of allowed WebSocket origins |
| `GEMINI_MODEL` | no | `gemini-2.5-flash` | Model id |
| `LOG_LEVEL` | no | `INFO` | Logging level |
| `HISTORY_TOKEN_BUDGET` | no | `4000` | Max token budget for context sent to the model |

The same `Settings` class is fed from three sources depending on environment: a local `.env` file (dev), Compose `environment:` (containers), and CI/Railway environment variables (deploy). Environment variables always take precedence over `.env`, and `.env` is never baked into the image.

## Architecture

```
Browser (templates/chat.html)
  → routers/ws.py      : origin + token check, accept, validation, rate limit
  → services/chat_service.py : token-budget context window, persist each turn
  → services/llm_provider.py : Gemini streaming behind an LLMProvider interface
  → db/repository.py   : all SQL/ORM access (ChatService stays SQL-agnostic)
  → PostgreSQL         : conversations + messages (durable history)
  ← chunks stream back → ws.py forwards to the browser
```

Layers, each with a single responsibility:

- **config** — validated settings from env / `.env`
- **schemas** — Pydantic message contracts (chunk / done / error / system / user / conversation)
- **services/llm_provider** — provider-agnostic LLM interface + `GeminiProvider`
- **services/chat_service** — history windowing (token budget), rate limit, streaming
- **services/connection_manager** — active connections (gauge) + message counter
- **db** — async SQLAlchemy engine, models, repository
- **routers** — HTTP (`/`, `/health`, `/metrics`) and WebSocket (`/ws`)
- **main** — lifespan (resource setup/teardown) + router wiring

## Key design decisions

- **Close codes:** 1008 for auth/origin rejection, 1011 for unexpected errors, 1012 from uvicorn on shutdown.
- **Errors never leak to the client:** internal exceptions are logged with a connection id; the client gets a generic message.
- **Rate limit:** sliding window over `time.monotonic()` (robust against clock changes).
- **Context window:** the full history lives in the DB; only a token-bounded slice is sent to the model — cost stays bounded.
- **LLM behind an interface:** swapping providers means writing one new class; tests inject a fake.
- **Resources in lifespan:** the Gemini client and connection manager are created once at startup, not per request.
- **Migrations:** schema changes are versioned with Alembic; the app runs `alembic upgrade head` on container start.
- **Single uvicorn worker:** per-connection WebSocket state (rate-limit list) is not shared across workers; scaling later requires shared state (e.g. Redis).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Chat UI |
| POST | `/auth/register` | Create account, returns a JWT |
| POST | `/auth/login` | Authenticate, returns a JWT |
| GET | `/health` | Liveness probe |
| GET | `/metrics` | `active_connections`, `total_messages` |
| GET | `/admin/stats` | Admin-only stats (role `admin`) |
| WS | `/ws?token=<jwt>&conversation_id=...` | Streaming chat (JWT-authenticated) |

## Authentication

Clients register or log in over HTTP to obtain a signed **JWT**, then present it on the WebSocket handshake (`?token=<jwt>`). The server resolves the user from the token, scopes conversations to their owner (no cross-user access — IDOR-protected), rate-limits per user, and gates admin endpoints behind a role check. Passwords are stored as bcrypt hashes; JWTs are signed (not encrypted), so no secrets go in the payload.

## CI

GitHub Actions runs `ruff` (lint) and `pytest` on every push and pull request, with a PostgreSQL service container available for tests.
