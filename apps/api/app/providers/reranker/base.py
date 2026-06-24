"""Cross-encoder reranker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RerankerProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def rerank(self, query: str, documents: list[dict], *, top_k: int) -> list[dict]:
        """Return documents sorted by relevance with optional `rerank_score` field."""
