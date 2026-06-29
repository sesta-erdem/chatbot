from app.services.chat_service import ChatService, estimate_tokens
from tests.conftest import TEST_USER_ID, FakeConversationRepository, FakeProvider


async def make_service(provider, history_token_budget=4000):
    """FakeConversationRepository ile DB'siz bir ChatService kurar; (service, repo) döndürür."""
    repo = FakeConversationRepository()
    conversation_id = await repo.create_conversation(TEST_USER_ID)
    service = ChatService(
        provider=provider,
        history_token_budget=history_token_budget,
        repo=repo,
        conversation_id=conversation_id,
    )
    return service, repo


async def collect(service: ChatService, message: str) -> str:
    parts = []
    async for chunk in service.stream_response(message):
        parts.append(chunk)
    return "".join(parts)


# --- token tahmini ---

def test_estimate_tokens_roughly_chars_over_four():
    assert estimate_tokens("") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 40) == 10


# --- stream ---

async def test_stream_returns_provider_chunks():
    service, _ = await make_service(FakeProvider(chunks=["hello ", "world"]))
    result = await collect(service, "merhaba")
    assert result == "hello world"


async def test_stream_appends_to_history_with_token_count():
    service, repo = await make_service(FakeProvider(chunks=["cevap"]))
    await collect(service, "soru")
    history = await repo.get_history(service._conversation_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "model"
    assert history[0].token_count >= 1
    assert history[1].token_count >= 1


# --- token bütçesi ile pencereleme ---

async def test_window_respects_token_budget():
    provider = FakeProvider(chunks=["x"])
    service, _ = await make_service(provider, history_token_budget=4)
    for i in range(10):
        await collect(service, f"msg{i}")
    assert len(provider.last_history) == 4


async def test_window_token_count_caps_at_budget():
    provider = FakeProvider(chunks=["x"])
    service, _ = await make_service(provider, history_token_budget=4)
    for i in range(10):
        await collect(service, f"msg{i}")
    assert await service.window_token_count() <= 4


async def test_window_grows_then_plateaus():
    provider = FakeProvider(chunks=["x"])
    service, _ = await make_service(provider, history_token_budget=4)
    sizes = []
    for i in range(6):
        sizes.append(len(provider.last_history))
        await collect(service, f"msg{i}")
    assert sizes[0] == 0
    assert max(sizes) == 4
    assert sizes[-1] == 4
