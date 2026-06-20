"""Deterministic mock embeddings — swap to OpenAI by setting OPENAI_API_KEY."""

import hashlib
import math

from app.core.config import settings
from app.providers.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    provider_name = "mock"

    def __init__(self):
        self.dimensions = settings.embedding_dimensions

    def _vector_for_text(self, text: str) -> list[float]:
        vec = []
        for i in range(self.dimensions):
            digest = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
            val = (int(digest[:6], 16) / 0xFFFFFF) * 2 - 1
            vec.append(val)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for_text(t) for t in texts]
