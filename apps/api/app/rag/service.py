"""RAG over financial knowledge — risk playbooks, strategy docs, SEC excerpts."""

from dataclasses import dataclass

import structlog

from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class RAGChunk:
    id: str
    content: str
    source: str
    score: float


class RAGService:
    """Vector search over pgvector (Phase 2) with keyword fallback for Phase 1."""

    PLAYBOOKS = [
        {
            "id": "risk-001",
            "source": "risk-playbook.md",
            "content": (
                "Never add to a tech-heavy portfolio when QQQ is below its 50-day moving average "
                "and VIX is rising. Reduce position size by 40% in high-volatility regimes."
            ),
            "keywords": ["qqq", "vix", "tech", "volatility", "exposure"],
        },
        {
            "id": "risk-002",
            "source": "risk-playbook.md",
            "content": (
                "Single-name concentration above 20% requires explicit user approval. "
                "NVDA, META, MSFT combined with QQQ creates hidden correlation risk."
            ),
            "keywords": ["concentration", "nvda", "meta", "msft", "qqq", "correlation"],
        },
        {
            "id": "risk-003",
            "source": "risk-playbook.md",
            "content": (
                "No market orders on volatile tickers. Use limit orders with defined stop loss. "
                "Do not trade in the first 10 minutes after market open."
            ),
            "keywords": ["market order", "limit", "stop", "open", "volatile"],
        },
    ]

    async def search(self, query: str, top_k: int = 3) -> list[RAGChunk]:
        if settings.openai_api_key:
            logger.info("rag_search", mode="keyword_fallback", query=query[:80])

        q = query.lower()
        scored = []
        for doc in self.PLAYBOOKS:
            hits = sum(1 for kw in doc["keywords"] if kw in q)
            if hits or any(word in doc["content"].lower() for word in q.split()[:5]):
                scored.append(
                    RAGChunk(
                        id=doc["id"],
                        content=doc["content"],
                        source=doc["source"],
                        score=float(hits + 0.1),
                    )
                )

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    async def embed_and_store(self, documents: list[dict]) -> int:
        """Phase 2: chunk, embed with OpenAI, store in pgvector."""
        logger.info("rag_ingest_stub", count=len(documents))
        return len(documents)
