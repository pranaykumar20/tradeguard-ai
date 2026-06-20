"""Embedding provider factory."""

from app.core.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.embeddings.mock import MockEmbeddingProvider
from app.providers.embeddings.openai import OpenAIEmbeddingProvider

_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        if settings.use_openai_embeddings:
            _provider = OpenAIEmbeddingProvider()
        else:
            _provider = MockEmbeddingProvider()
    return _provider
