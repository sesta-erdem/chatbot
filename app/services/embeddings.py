from typing import Protocol, runtime_checkable

from google import genai
from google.genai import types


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Metni anlam vektörüne çevirir. Sorgu ve doküman AYNI modelden embed edilmeli."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbeddingProvider:
    def __init__(self, client: genai.Client, model: str, dim: int) -> None:
        self._client = client
        self._model = model
        # DB şeması Vector(dim) — modelin varsayılanı ne olursa olsun bu boyutu iste.
        self._config = types.EmbedContentConfig(output_dimensionality=dim)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        result = await self._client.aio.models.embed_content(
            model=self._model, contents=texts, config=self._config
        )
        return [embedding.values for embedding in result.embeddings]
