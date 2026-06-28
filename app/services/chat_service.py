import time
import uuid
from typing import AsyncIterator

from google.genai import types

from app.db.models import Message
from app.db.repository import ConversationRepository
from app.services.llm_provider import LLMProvider

RATE_LIMIT_WINDOW = 10.0
RATE_LIMIT_MAX_MESSAGES = 5


class RateLimitExceeded(Exception):
    pass


def estimate_tokens(text: str) -> int:
    """Kaba token tahmini (~4 karakter = 1 token). Kesin sayım için modelin
    tokenizer'ı/usage_metadata'sı gerekir; bağlam bütçesi için bu yaklaşım yeterli."""
    return max(1, len(text) // 4)


class ChatService:
    """
    Bir bağlantının sohbet mantığı.
    Geçmiş DB'de (repository üzerinden) — bağlantı ölse de kalıcı.
    Modele giden bağlam TOKEN BÜTÇESİYLE sınırlanır: en yeni mesajlardan geriye
    doğru, bütçe dolana kadar mesaj alınır ("kayıt" tam, "bağlam" sınırlı).
    """

    def __init__(
        self,
        provider: LLMProvider,
        history_token_budget: int,
        repo: ConversationRepository,
        conversation_id: uuid.UUID,
    ) -> None:
        self._provider = provider
        self._budget = history_token_budget
        self._repo = repo
        self._conversation_id = conversation_id
        self._timestamps: list[float] = []

    def check_rate_limit(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if t > now - RATE_LIMIT_WINDOW]
        if len(self._timestamps) >= RATE_LIMIT_MAX_MESSAGES:
            raise RateLimitExceeded(f"pencerede {len(self._timestamps)} mesaj")
        self._timestamps.append(now)

    async def _windowed_messages(self) -> list[Message]:
        """DB'deki tam geçmişten, token bütçesine sığan en yeni mesajları seç (kronolojik döner)."""
        messages = await self._repo.get_history(self._conversation_id)
        selected: list[Message] = []
        used = 0
        for message in reversed(messages):
            if selected and used + message.token_count > self._budget:
                break
            used += message.token_count
            selected.append(message)
        selected.reverse()
        return selected

    async def _windowed_history(self) -> list[types.Content]:
        return [
            types.Content(role=m.role, parts=[types.Part(text=m.content)])
            for m in await self._windowed_messages()
        ]

    async def window_token_count(self) -> int:
        return sum(m.token_count for m in await self._windowed_messages())

    async def stream_response(self, message: str) -> AsyncIterator[str]:
        windowed = await self._windowed_history()
        full_response: list[str] = []

        async for chunk in self._provider.stream(message, windowed):
            full_response.append(chunk)
            yield chunk

        # Hata olmadan tamamlandıysa hem soruyu hem cevabı token sayısıyla DB'ye yaz
        text = "".join(full_response)
        await self._repo.append_message(self._conversation_id, "user", message, estimate_tokens(message))
        await self._repo.append_message(self._conversation_id, "model", text, estimate_tokens(text))
