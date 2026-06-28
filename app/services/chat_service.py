import time
import uuid
from typing import AsyncIterator

from google.genai import types

from app.db.repository import ConversationRepository
from app.services.llm_provider import LLMProvider

RATE_LIMIT_WINDOW = 10.0
RATE_LIMIT_MAX_MESSAGES = 5


class RateLimitExceeded(Exception):
    pass


class ChatService:
    """
    Bir bağlantının sohbet mantığı.
    Geçmiş artık bellekte değil DB'de (repository üzerinden) — bağlantı ölse de kalıcı.
    Rate limit ise bağlantıya özel kalır (bellekte timestamps).
    """

    def __init__(
        self,
        provider: LLMProvider,
        history_window: int,
        repo: ConversationRepository,
        conversation_id: uuid.UUID,
    ) -> None:
        self._provider = provider
        self._history_window = history_window
        self._repo = repo
        self._conversation_id = conversation_id
        self._timestamps: list[float] = []

    def check_rate_limit(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if t > now - RATE_LIMIT_WINDOW]
        if len(self._timestamps) >= RATE_LIMIT_MAX_MESSAGES:
            raise RateLimitExceeded(f"pencerede {len(self._timestamps)} mesaj")
        self._timestamps.append(now)

    async def _windowed_history(self) -> list[types.Content]:
        """DB'deki TAM geçmişten son N turn'ü seç ve Gemini formatına çevir (1 turn = user + model)."""
        messages = await self._repo.get_history(self._conversation_id)
        windowed = messages[-(self._history_window * 2):]
        return [
            types.Content(role=m.role, parts=[types.Part(text=m.content)])
            for m in windowed
        ]

    async def turns_in_window(self) -> int:
        messages = await self._repo.get_history(self._conversation_id)
        return len(messages[-(self._history_window * 2):]) // 2

    async def stream_response(self, message: str) -> AsyncIterator[str]:
        windowed = await self._windowed_history()
        full_response: list[str] = []

        async for chunk in self._provider.stream(message, windowed):
            full_response.append(chunk)
            yield chunk

        # Hata olmadan tamamlandıysa hem soruyu hem cevabı DB'ye yaz (kalıcı geçmiş)
        await self._repo.append_message(self._conversation_id, "user", message)
        await self._repo.append_message(self._conversation_id, "model", "".join(full_response))
