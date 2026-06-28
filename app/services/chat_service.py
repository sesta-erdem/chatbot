import time
from typing import AsyncIterator

from google.genai import types

from app.services.llm_provider import LLMProvider

RATE_LIMIT_WINDOW = 10.0
RATE_LIMIT_MAX_MESSAGES = 5


class RateLimitExceeded(Exception):
    pass


class ChatService:
    def __init__(self, provider: LLMProvider, history_window: int) -> None:
        self._provider = provider
        self._history_window = history_window
        self._history: list[types.Content] = []
        self._timestamps: list[float] = []

    def check_rate_limit(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if t > now - RATE_LIMIT_WINDOW]
        if len(self._timestamps) >= RATE_LIMIT_MAX_MESSAGES:
            raise RateLimitExceeded(f"pencerede {len(self._timestamps)} mesaj")
        self._timestamps.append(now)

    def turns_in_window(self) -> int:
        windowed = self._history[-(self._history_window * 2):]
        return len(windowed) // 2

    async def stream_response(self, message: str) -> AsyncIterator[str]:
        windowed = self._history[-(self._history_window * 2):]
        full_response: list[str] = []

        async for chunk in self._provider.stream(message, windowed):
            full_response.append(chunk)
            yield chunk

        self._history.append(types.Content(role="user", parts=[types.Part(text=message)]))
        self._history.append(types.Content(role="model", parts=[types.Part(text="".join(full_response))]))
