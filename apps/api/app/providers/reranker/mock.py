"""Mock cross-encoder reranker — lexical overlap scoring."""

from __future__ import annotations

from app.providers.reranker.base import RerankerProvider
from app.rag.retrieval import keyword_score


class MockRerankerProvider(RerankerProvider):
    provider_name: str = "mock"

    async def rerank(self, query: str, documents: list[dict], *, top_k: int) -> list[dict]:
        scored = []
        for doc in documents:
            content = doc.get("content", "")
            score = keyword_score(query, content)
            scored.append({**doc, "rerank_score": score})
        scored.sort(key=lambda row: row.get("rerank_score", 0), reverse=True)
        return scored[:top_k]
