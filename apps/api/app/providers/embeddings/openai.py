"""OpenAI embeddings — activated when OPENAI_API_KEY is set."""

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.embeddings.mock import MockEmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider_name = "openai"

    def __init__(self):
        self.dimensions = settings.embedding_dimensions
        self._fallback = MockEmbeddingProvider()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def embed_texts(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        if not self._client:
            return await self._fallback.embed_texts(texts)
        try:
            resp = await self._client.embeddings.create(
                model=model or settings.embedding_model,
                input=texts,
            )
            return [item.embedding for item in resp.data]
        except Exception:
            return await self._fallback.embed_texts(texts)
