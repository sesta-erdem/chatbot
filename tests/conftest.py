import uuid
from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app.main import app
from app.services.auth import create_access_token
from app.services.llm_provider import LLMProvider


class FakeProvider:
    """Gemini API çağırmadan sabit yanıt döndüren test provider'ı."""

    def __init__(self, chunks: list[str] | None = None) -> None:
        self.chunks = chunks or ["merhaba ", "dünya"]
        self.call_count = 0
        self.last_history: list[types.Content] = []

    async def stream(self, message: str, history: list[types.Content]) -> AsyncIterator[str]:
        self.call_count += 1
        self.last_history = list(history)
        for chunk in self.chunks:
            yield chunk


assert isinstance(FakeProvider(), LLMProvider)


class FakeConversationRepository:
    """DB'siz konuşma deposu (sahiplik dahil)."""

    def __init__(self) -> None:
        self._messages: dict[uuid.UUID, list] = {}
        self._owners: dict[uuid.UUID, uuid.UUID] = {}

    def seed_conversation(self, user_id: uuid.UUID) -> uuid.UUID:
        """Test için senkron konuşma oluşturma."""
        cid = uuid.uuid4()
        self._messages[cid] = []
        self._owners[cid] = user_id
        return cid

    async def create_conversation(self, user_id: uuid.UUID) -> uuid.UUID:
        cid = uuid.uuid4()
        self._messages[cid] = []
        self._owners[cid] = user_id
        return cid

    async def belongs_to(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self._owners.get(conversation_id) == user_id

    async def append_message(self, conversation_id, role, content, token_count=0) -> None:
        self._messages.setdefault(conversation_id, []).append(
            SimpleNamespace(role=role, content=content, token_count=token_count)
        )

    async def get_history(self, conversation_id):
        return list(self._messages.get(conversation_id, []))


class FakeUserRepository:
    """DB'siz kullanıcı deposu."""

    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, SimpleNamespace] = {}
        self._by_email: dict[str, SimpleNamespace] = {}

    def seed(self, user_id, email, role="user", password_hash="x") -> SimpleNamespace:
        user = SimpleNamespace(id=user_id, email=email, role=role, password_hash=password_hash)
        self._by_id[user_id] = user
        self._by_email[email] = user
        return user

    async def create_user(self, email, password_hash, role="user") -> SimpleNamespace:
        return self.seed(uuid.uuid4(), email, role, password_hash)

    async def get_by_email(self, email):
        return self._by_email.get(email)

    async def get_by_id(self, user_id):
        return self._by_id.get(user_id)


TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ADMIN_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ORIGIN = "http://127.0.0.1:8000"
USER_TOKEN = create_access_token(TEST_USER_ID, "user")
ADMIN_TOKEN = create_access_token(ADMIN_USER_ID, "admin")


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def user_repo():
    repo = FakeUserRepository()
    repo.seed(TEST_USER_ID, "me@test.com", "user")
    repo.seed(ADMIN_USER_ID, "admin@test.com", "admin")
    return repo


@pytest.fixture
def conv_repo():
    return FakeConversationRepository()


@pytest.fixture
def client(monkeypatch, user_repo, conv_repo):
    """Gerçek DB/Gemini/JWT-kullanıcı yerine fake'lerle TestClient."""
    import app.config as cfg
    import app.dependencies as deps_module
    import app.routers.auth as auth_module
    import app.routers.ws as ws_module

    monkeypatch.setattr(cfg.settings, "allowed_origins", [ORIGIN])
    monkeypatch.setattr(cfg.settings, "history_token_budget", 4000)
    monkeypatch.setattr(ws_module.settings, "allowed_origins", [ORIGIN])
    monkeypatch.setattr(ws_module.settings, "history_token_budget", 4000)

    # Repository sınıflarını paylaşılan fake örnekleri döndüren fabrikalarla değiştir
    monkeypatch.setattr(ws_module, "ConversationRepository", lambda: conv_repo)
    monkeypatch.setattr(ws_module, "UserRepository", lambda: user_repo)
    monkeypatch.setattr(auth_module, "UserRepository", lambda: user_repo)
    monkeypatch.setattr(deps_module, "UserRepository", lambda: user_repo)

    with TestClient(app) as c:
        app.state.genai_client = MagicMock()
        yield c
