from app.services.chat_service import RAG_INSTRUCTION, ChatService
from app.services.ingestion import chunk_pages, chunk_text
from tests.conftest import (
    TEST_USER_ID,
    FakeConversationRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeProvider,
)


async def make_rag_service(provider, hits, top_k=4, threshold=0.65):
    repo = FakeConversationRepository()
    cid = await repo.create_conversation(TEST_USER_ID)
    return ChatService(
        provider=provider,
        history_token_budget=4000,
        repo=repo,
        conversation_id=cid,
        embedder=FakeEmbeddingProvider(),
        doc_repo=FakeDocumentRepository(hits=hits),
        user_id=TEST_USER_ID,
        rag_top_k=top_k,
        rag_distance_threshold=threshold,
    )


async def collect(service, message):
    return "".join([c async for c in service.stream_response(message)])


# --- chunking (saf fonksiyonlar) ---

def test_chunk_text_overlap():
    text = "a" * 1000
    chunks = chunk_text(text, size=400, overlap=100)
    assert chunks[0] == "a" * 400
    # 400'lük parçalar 100 overlap ile: başlangıçlar 0, 300, 600 → 3 parça
    assert len(chunks) == 3


def test_chunk_text_empty():
    assert chunk_text("   ", size=100, overlap=10) == []


def test_chunk_pages_keeps_page_number():
    pages = [(1, "x" * 50), (2, "y" * 50)]
    out = chunk_pages(pages, size=100, overlap=0)
    assert out[0][0] == 1 and out[1][0] == 2


# --- RAG retrieval ---

async def test_rag_injects_context_and_sources():
    provider = FakeProvider(chunks=["cevap"])
    hits = [{"content": "Erdem bir Tekla çizericisidir.", "page": 3, "filename": "cv.pdf", "distance": 0.2}]
    service = await make_rag_service(provider, hits)

    await collect(service, "Erdem ne iş yapar?")

    # Prompt'a bağlam + RAG talimatı + kaynak girmiş olmalı
    assert RAG_INSTRUCTION in provider.last_message
    assert "cv.pdf" in provider.last_message
    assert service.last_sources == [{"file": "cv.pdf", "page": 3}]


async def test_rag_below_threshold_no_context():
    provider = FakeProvider(chunks=["cevap"])
    # distance eşik üstünde → alakasız → bağlam yok
    hits = [{"content": "alakasız", "page": 1, "filename": "x.pdf", "distance": 0.9}]
    service = await make_rag_service(provider, hits, threshold=0.65)

    await collect(service, "soru")

    assert provider.last_message == "soru"  # ham soru, bağlam yok
    assert service.last_sources == []


async def test_rag_no_documents_plain_prompt():
    provider = FakeProvider(chunks=["cevap"])
    service = await make_rag_service(provider, hits=[])

    await collect(service, "merhaba")

    assert provider.last_message == "merhaba"
    assert service.last_sources == []


class BrokenEmbedder:
    """Embedding API'sinin çöktüğü senaryo (ör. model 404, kota, ağ)."""

    async def embed(self, texts):
        raise RuntimeError("embedding API down")


async def test_rag_failure_does_not_kill_chat():
    # RAG zenginleştirmedir: embedder çökerse sohbet BAĞLAMSIZ devam etmeli.
    provider = FakeProvider(chunks=["cevap"])
    repo = FakeConversationRepository()
    cid = await repo.create_conversation(TEST_USER_ID)
    service = ChatService(
        provider=provider,
        history_token_budget=4000,
        repo=repo,
        conversation_id=cid,
        embedder=BrokenEmbedder(),
        doc_repo=FakeDocumentRepository(hits=[]),
        user_id=TEST_USER_ID,
    )

    result = await collect(service, "merhaba")

    assert result == "cevap"                    # yanıt aktı
    assert provider.last_message == "merhaba"   # ham soru gitti (bağlamsız)
    assert service.last_sources == []
