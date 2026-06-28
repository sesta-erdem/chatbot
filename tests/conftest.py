import uuid
from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app.main import app
from app.services.llm_provider import LLMProvider


class FakeProvider:
    """Gemini API çağırmadan sabit yanıt döndüren test provider'ı."""

    def __init__(self, chunks: list[str] | None = None) -> None:
        self.chunks = chunks or ["merhaba ", "dünya"]
        self.call_count = 0
        self.last_history: list[types.Content] = []

    async def stream(
        self,
        message: str,
        history: list[types.Content],
    ) -> AsyncIterator[str]:
        self.call_count += 1
        self.last_history = list(history)
        for chunk in self.chunks:
            yield chunk


assert isinstance(FakeProvider(), LLMProvider)


class FakeRepository:
    """DB'ye çarpmadan mesajları bellekte tutan test repository'si (ConversationRepository yerine)."""

    def __init__(self) -> None:
        self._messages: dict[uuid.UUID, list] = {}

    async def create_conversation(self) -> uuid.UUID:
        cid = uuid.uuid4()
        self._messages[cid] = []
        return cid

    async def exists(self, conversation_id: uuid.UUID) -> bool:
        return conversation_id in self._messages

    async def append_message(self, conversation_id, role, content, token_count=0) -> None:
        self._messages.setdefault(conversation_id, []).append(
            SimpleNamespace(role=role, content=content, token_count=token_count)
        )

    async def get_history(self, conversation_id):
        return list(self._messages.get(conversation_id, []))


TOKEN = "test-token-123"
ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def client(monkeypatch):
    """Gerçek Gemini client yerine MagicMock kullanan TestClient."""
    import app.config as cfg
    import app.routers.ws as ws_module

    # settings singleton'ı zaten yüklenmiş; attribute'ları doğrudan patch et
    monkeypatch.setattr(cfg.settings, "app_access_token", TOKEN)
    monkeypatch.setattr(cfg.settings, "allowed_origins", [ORIGIN])
    monkeypatch.setattr(cfg.settings, "history_window", 5)
    monkeypatch.setattr(ws_module.settings, "app_access_token", TOKEN)
    monkeypatch.setattr(ws_module.settings, "allowed_origins", [ORIGIN])
    monkeypatch.setattr(ws_module.settings, "history_window", 5)

    # Gerçek DB'ye çarpmamak için repository'yi FakeRepository ile değiştir
    monkeypatch.setattr(ws_module, "ConversationRepository", FakeRepository)

    with TestClient(app) as c:
        app.state.genai_client = MagicMock()
        yield c
