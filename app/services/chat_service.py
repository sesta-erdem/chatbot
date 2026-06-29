import uuid
from typing import AsyncIterator

from google.genai import types

from app.db.models import Message
from app.db.repository import ConversationRepository, DocumentRepository
from app.services.embeddings import EmbeddingProvider
from app.services.llm_provider import LLMProvider

RAG_INSTRUCTION = (
    "Aşağıdaki PASAJLARA dayanarak cevap ver. Cevap pasajlarda yoksa uydurma; "
    "'Dokümanlarda bulamadım' de. Kullandığın bilgiyi pasajlardaki kaynaklarla destekle."
)


def estimate_tokens(text: str) -> int:
    """Kaba token tahmini (~4 karakter = 1 token). Kesin sayım için modelin
    tokenizer'ı/usage_metadata'sı gerekir; bağlam bütçesi için bu yaklaşım yeterli."""
    return max(1, len(text) // 4)


class ChatService:
    """
    Bir bağlantının sohbet mantığı.
    Geçmiş DB'de (repository üzerinden) — bağlantı ölse de kalıcı.
    Modele giden bağlam TOKEN BÜTÇESİYLE sınırlanır.
    RAG açıksa (embedder + doc_repo + user_id verilmişse): soru embed edilir,
    kullanıcının dokümanlarından en yakın parçalar bulunur, eşik altındakiler
    bağlam olarak prompt'a eklenir ve kaynaklar last_sources'a yazılır.
    """

    def __init__(
        self,
        provider: LLMProvider,
        history_token_budget: int,
        repo: ConversationRepository,
        conversation_id: uuid.UUID,
        embedder: EmbeddingProvider | None = None,
        doc_repo: DocumentRepository | None = None,
        user_id: uuid.UUID | None = None,
        rag_top_k: int = 4,
        rag_distance_threshold: float = 0.65,
    ) -> None:
        self._provider = provider
        self._budget = history_token_budget
        self._repo = repo
        self._conversation_id = conversation_id
        self._embedder = embedder
        self._doc_repo = doc_repo
        self._user_id = user_id
        self._top_k = rag_top_k
        self._threshold = rag_distance_threshold
        self.last_sources: list[dict] = []

    async def _windowed_messages(self) -> list[Message]:
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

    async def _retrieve(self, question: str) -> tuple[str, list[dict]]:
        """Soru için bağlam metni + kaynak listesi üret. RAG kapalıysa boş döner."""
        if not (self._embedder and self._doc_repo and self._user_id):
            return "", []
        query_vec = (await self._embedder.embed([question]))[0]
        hits = await self._doc_repo.search(self._user_id, query_vec, self._top_k)
        hits = [h for h in hits if h["distance"] <= self._threshold]
        if not hits:
            return "", []
        context = "\n\n".join(
            f"[{h['filename']} s.{h['page']}] {h['content']}" for h in hits
        )
        sources = [{"file": h["filename"], "page": h["page"]} for h in hits]
        return context, sources

    async def stream_response(self, message: str) -> AsyncIterator[str]:
        windowed = await self._windowed_history()
        self.last_sources = []

        context, sources = await self._retrieve(message)
        if context:
            self.last_sources = sources
            prompt = f"{RAG_INSTRUCTION}\n\n[PASAJLAR]\n{context}\n\n[SORU]\n{message}"
        else:
            prompt = message

        full_response: list[str] = []
        async for chunk in self._provider.stream(prompt, windowed):
            full_response.append(chunk)
            yield chunk

        # DB'ye ORİJİNAL soru yazılır (bağlamla şişirilmiş prompt değil) — geçmiş temiz kalır
        text = "".join(full_response)
        await self._repo.append_message(self._conversation_id, "user", message, estimate_tokens(message))
        await self._repo.append_message(self._conversation_id, "model", text, estimate_tokens(text))
