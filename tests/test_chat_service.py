import uuid

import pytest

from app.services.chat_service import ChatService, RateLimitExceeded
from tests.conftest import FakeProvider, FakeRepository


async def make_service(provider, history_window=5):
    """FakeRepository ile DB'siz bir ChatService kurar; (service, repo) döndürür."""
    repo = FakeRepository()
    conversation_id = await repo.create_conversation()
    service = ChatService(
        provider=provider,
        history_window=history_window,
        repo=repo,
        conversation_id=conversation_id,
    )
    return service, repo


async def collect(service: ChatService, message: str) -> str:
    parts = []
    async for chunk in service.stream_response(message):
        parts.append(chunk)
    return "".join(parts)


# --- stream ---

async def test_stream_returns_provider_chunks():
    service, _ = await make_service(FakeProvider(chunks=["hello ", "world"]))
    result = await collect(service, "merhaba")
    assert result == "hello world"


async def test_stream_appends_to_history():
    service, repo = await make_service(FakeProvider(chunks=["cevap"]))
    await collect(service, "soru")
    history = await repo.get_history(service._conversation_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "model"


# --- history windowing ---

async def test_window_limits_history_sent_to_provider():
    provider = FakeProvider(chunks=["x"])
    service, _ = await make_service(provider, history_window=2)

    # 4 mesaj gönder — window=2 demek max 2 turn (4 Content)
    for i in range(4):
        await collect(service, f"msg{i}")

    # 5. mesajda provider'a gönderilen history en fazla 4 Content olmalı (2 turn)
    await collect(service, "son mesaj")
    assert len(provider.last_history) <= 4


async def test_window_plateaus_at_max():
    provider = FakeProvider(chunks=["y"])
    service, _ = await make_service(provider, history_window=3)

    for i in range(10):
        await collect(service, f"msg{i}")

    # Toplam history 20 Content olsa da son çağrıda max 6 (3 turn) gitmeli
    assert len(provider.last_history) == 6


async def test_turns_in_window_increments_then_plateaus():
    provider = FakeProvider(chunks=["z"])
    service, _ = await make_service(provider, history_window=3)

    counts = []
    for i in range(6):
        counts.append(await service.turns_in_window())
        await collect(service, f"msg{i}")

    # 0, 1, 2, 3, 3, 3
    assert counts == [0, 1, 2, 3, 3, 3]


# --- rate limit ---

async def test_rate_limit_passes_under_max():
    service, _ = await make_service(FakeProvider())
    for _ in range(5):
        service.check_rate_limit()  # 5 kez geçmeli


async def test_rate_limit_raises_on_sixth():
    service, _ = await make_service(FakeProvider())
    for _ in range(5):
        service.check_rate_limit()
    with pytest.raises(RateLimitExceeded):
        service.check_rate_limit()


async def test_rate_limit_resets_after_window():
    service, _ = await make_service(FakeProvider())

    # 5 mesaj gönder, sonra zamanı 11 saniye ileri al
    for _ in range(5):
        service.check_rate_limit()

    # Zamanı sahte olarak 11s ileri sarmak için _timestamps'i elle güncelle
    service._timestamps = [t - 11 for t in service._timestamps]

    # Artık geçmeli — pencere dışına çıktı
    service.check_rate_limit()  # raise etmemeli
