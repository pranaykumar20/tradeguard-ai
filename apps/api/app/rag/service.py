"""RAG over financial knowledge — vector search with mock or OpenAI embeddings."""

from dataclasses import dataclass

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.providers.embeddings.factory import get_embedding_provider

logger = structlog.get_logger()

PLAYBOOKS = [
    {
        "id": "risk-001",
        "source": "risk-playbook.md",
        "content": (
            "Never add to a tech-heavy portfolio when QQQ is below its 50-day moving average "
            "and VIX is rising. Reduce position size by 40% in high-volatility regimes."
        ),
    },
    {
        "id": "risk-002",
        "source": "risk-playbook.md",
        "content": (
            "Single-name concentration above 20% requires explicit user approval. "
            "NVDA, META, MSFT combined with QQQ creates hidden correlation risk."
        ),
    },
    {
        "id": "risk-003",
        "source": "risk-playbook.md",
        "content": (
            "No market orders on volatile tickers. Use limit orders with defined stop loss. "
            "Do not trade in the first 10 minutes after market open."
        ),
    },
    {
        "id": "risk-004",
        "source": "risk-playbook.md",
        "content": (
            "Daily loss circuit breaker: halt all new trades when daily P&L exceeds the "
            "configured loss limit. Review open positions before resuming."
        ),
    },
    {
        "id": "risk-005",
        "source": "position-sizing.md",
        "content": (
            "Maximum trade size is $250 in Phase 1. Scale into positions over multiple days "
            "rather than adding full size in one order when RSI is above 70."
        ),
    },
    {
        "id": "risk-006",
        "source": "sector-rules.md",
        "content": (
            "Technology sector exposure above 30% triggers CAUTION on new tech buys. "
            "Consider diversifying into healthcare or consumer names before adding NVDA or META."
        ),
    },
    {
        "id": "risk-007",
        "source": "options-policy.md",
        "content": (
            "Options are blocked in Phase 1 without explicit manual approval. "
            "Stocks and ETFs only on the allowed ticker list."
        ),
    },
]


@dataclass
class RAGChunk:
    id: str
    content: str
    source: str
    score: float


class RAGService:
    _seeded = False

    async def ensure_index(self) -> int:
        if RAGService._seeded:
            storage = await get_storage()
            # cheap check — re-seed only if empty
            results = await storage.search_rag([0.0] * settings.embedding_dimensions, top_k=1)
            if results:
                return 0

        provider = get_embedding_provider()
        storage = await get_storage()
        texts = [p["content"] for p in PLAYBOOKS]
        embeddings = await provider.embed_texts(texts)
        docs = []
        for playbook, emb in zip(PLAYBOOKS, embeddings, strict=True):
            docs.append(
                {
                    "chunk_id": playbook["id"],
                    "source": playbook["source"],
                    "content": playbook["content"],
                    "embedding": emb,
                    "meta": {"keywords": playbook["id"]},
                }
            )
        count = await storage.upsert_rag_documents(docs)
        RAGService._seeded = True
        logger.info("rag_index_ready", chunks=count, provider=provider.provider_name)
        return count

    async def search(self, query: str, top_k: int = 3) -> list[RAGChunk]:
        await self.ensure_index()
        provider = get_embedding_provider()
        query_vec = await provider.embed_text(query)
        storage = await get_storage()
        rows = await storage.search_rag(query_vec, top_k=top_k)

        if not rows:
            return self._keyword_fallback(query, top_k)

        return [
            RAGChunk(
                id=r.get("chunk_id") or r.get("id", ""),
                content=r["content"],
                source=r.get("source", ""),
                score=float(r.get("score", 0)),
            )
            for r in rows
        ]

    def _keyword_fallback(self, query: str, top_k: int) -> list[RAGChunk]:
        q = query.lower()
        scored = []
        for doc in PLAYBOOKS:
            hits = sum(1 for word in q.split() if len(word) > 3 and word in doc["content"].lower())
            if hits:
                scored.append(
                    RAGChunk(id=doc["id"], content=doc["content"], source=doc["source"], score=float(hits))
                )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    async def embed_and_store(self, documents: list[dict]) -> int:
        provider = get_embedding_provider()
        storage = await get_storage()
        texts = [d["content"] for d in documents]
        embeddings = await provider.embed_texts(texts)
        docs = []
        for doc, emb in zip(documents, embeddings, strict=True):
            docs.append(
                {
                    "chunk_id": doc.get("chunk_id") or doc.get("id"),
                    "source": doc.get("source", "upload"),
                    "content": doc["content"],
                    "embedding": emb,
                    "meta": doc.get("meta"),
                }
            )
        return await storage.upsert_rag_documents(docs)
