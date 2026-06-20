"""RAG over financial knowledge — hybrid vector + keyword retrieval."""

from dataclasses import dataclass

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.providers.embeddings.factory import get_embedding_provider
from app.rag.playbooks import playbook_fallback_chunks
from app.rag.retrieval import (
    hybrid_merge,
    infer_doc_types,
    keyword_score,
    rerank_candidates,
    rewrite_query,
)

logger = structlog.get_logger()


@dataclass
class RAGChunk:
    id: str
    content: str
    source: str
    score: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "score": round(self.score, 4),
        }


def format_chunks_for_context(chunks: list[RAGChunk]) -> str:
    if not chunks:
        return ""
    lines = ["Relevant knowledge:"]
    for chunk in chunks:
        lines.append(f"- [{chunk.source}] {chunk.content}")
    return "\n".join(lines)


class RAGService:
    _seeded = False

    @classmethod
    def mark_ready(cls) -> None:
        cls._seeded = True

    async def has_documents(self) -> bool:
        storage = await get_storage()
        results = await storage.search_rag([0.0] * settings.embedding_dimensions, top_k=1)
        return bool(results)

    async def ensure_index(self) -> int:
        if self._seeded:
            return 0
        from app.rag.indexer import RAGIndexer

        result = await RAGIndexer().ensure_initialized()
        return int(result.get("total", 0))

    async def _vector_candidates(
        self,
        query_vec: list[float],
        *,
        pool: int,
        ticker: str | None,
        doc_types: list[str] | None,
    ) -> list[dict]:
        storage = await get_storage()
        if doc_types and settings.rag_type_routing_enabled:
            merged: dict[str, dict] = {}
            per_type = max(3, pool // len(doc_types))
            for doc_type in doc_types:
                hits = await storage.search_rag(
                    query_vec,
                    top_k=per_type,
                    ticker=ticker,
                    doc_types=[doc_type],
                )
                for hit in hits:
                    chunk_id = hit.get("chunk_id") or hit.get("id", "")
                    existing = merged.get(chunk_id)
                    if not existing or hit.get("score", 0) > existing.get("score", 0):
                        merged[chunk_id] = hit
            ranked = sorted(merged.values(), key=lambda row: row.get("score", 0), reverse=True)
            return ranked[:pool]

        return await storage.search_rag(
            query_vec,
            top_k=pool,
            ticker=ticker,
            doc_types=doc_types,
        )

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[RAGChunk]:
        top_k = top_k or settings.rag_top_k
        await self.ensure_index()

        preferred_types = doc_types if doc_types is not None else infer_doc_types(query)
        search_query = rewrite_query(query, ticker)
        pool = settings.rag_candidate_pool

        provider = get_embedding_provider()
        query_vec = await provider.embed_text(search_query)
        storage = await get_storage()

        vector_hits = await self._vector_candidates(
            query_vec,
            pool=pool,
            ticker=ticker,
            doc_types=preferred_types,
        )

        corpus = await storage.list_rag_documents(ticker=ticker, doc_types=preferred_types)
        keyword_ranked = sorted(
            corpus,
            key=lambda doc: keyword_score(query, doc.get("content", "")),
            reverse=True,
        )[:pool]

        if not vector_hits and not keyword_ranked:
            if doc_types is not None:
                return []
            return self._keyword_fallback(query, top_k, ticker=ticker)

        hybrid_scores = hybrid_merge(query, vector_hits, keyword_ranked)
        candidate_map: dict[str, dict] = {}
        for doc in vector_hits + keyword_ranked:
            chunk_id = doc.get("chunk_id") or doc.get("id", "")
            candidate_map.setdefault(chunk_id, doc)

        ranked = rerank_candidates(
            query,
            list(candidate_map.values()),
            hybrid_scores=hybrid_scores,
            preferred_types=preferred_types,
            top_k=top_k,
        )

        return [
            RAGChunk(
                id=item.chunk_id,
                content=item.content,
                source=item.source,
                score=item.final_score,
            )
            for item in ranked
        ]

    def _keyword_fallback(
        self, query: str, top_k: int, ticker: str | None = None
    ) -> list[RAGChunk]:
        q = query.lower()
        scored = []
        for doc in playbook_fallback_chunks():
            hits = sum(
                1 for word in q.split() if len(word) > 3 and word in doc["content"].lower()
            )
            kw = keyword_score(query, doc["content"])
            combined = float(hits) + kw
            if combined > 0:
                scored.append(
                    RAGChunk(
                        id=doc["chunk_id"],
                        content=doc["content"],
                        source=doc["source"],
                        score=combined,
                    )
                )
        if ticker:
            ticker_lower = ticker.lower()
            scored.sort(
                key=lambda c: (
                    ticker_lower in c.content.lower(),
                    c.score,
                ),
                reverse=True,
            )
        else:
            scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    async def embed_and_store(self, documents: list[dict]) -> int:
        if not documents:
            return 0
        provider = get_embedding_provider()
        storage = await get_storage()
        texts = [d["content"] for d in documents]
        embeddings = await provider.embed_texts(texts)
        docs = []
        for doc, emb in zip(documents, embeddings, strict=True):
            meta = dict(doc.get("meta") or {})
            meta.setdefault("type", "document")
            docs.append(
                {
                    "chunk_id": doc.get("chunk_id") or doc.get("id"),
                    "source": doc.get("source", "upload"),
                    "content": doc["content"],
                    "embedding": emb,
                    "meta": meta,
                }
            )
        count = await storage.upsert_rag_documents(docs)
        self.mark_ready()
        return count
