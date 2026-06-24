"""RAG over financial knowledge — hybrid vector + keyword retrieval."""

from dataclasses import dataclass

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.providers.embeddings.factory import get_embedding_provider
from app.providers.reranker.factory import get_reranker_provider
from app.rag.cache import (
    embedding_cache_key,
    get_cached_embedding,
    get_cached_results,
    result_cache_key,
    set_cached_embedding,
    set_cached_results,
)
from app.rag.playbooks import playbook_fallback_chunks
from app.rag.retrieval import (
    ScoredDocument,
    apply_news_freshness_cutoff,
    apply_temporal_filter,
    enrich_filing_parent_context,
    hybrid_merge,
    infer_doc_types,
    keyword_score,
    rerank_candidates,
    rewrite_query,
    should_use_cross_encoder,
    staleness_label,
)

logger = structlog.get_logger()


@dataclass
class RAGChunk:
    id: str
    content: str
    source: str
    score: float
    doc_type: str = "document"
    meta: dict | None = None

    def to_dict(self) -> dict:
        meta = self.meta or {}
        filed_at = meta.get("filed_at") or meta.get("published_at") or meta.get("as_of")
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "score": round(self.score, 4),
            "doc_type": meta.get("type", self.doc_type),
            "section": meta.get("section"),
            "filed_at": filed_at,
            "url": meta.get("url"),
            "ingested_at": meta.get("ingested_at"),
        }


def chunk_from_ranked(item, *, doc_type: str | None = None) -> RAGChunk:
    meta = item.meta or {}
    return RAGChunk(
        id=item.chunk_id,
        content=item.content,
        source=item.source,
        score=item.final_score,
        doc_type=doc_type or meta.get("type", "document"),
        meta=meta,
    )


def format_chunks_for_context(chunks: list[RAGChunk]) -> str:
    if not chunks:
        return ""
    lines = ["Relevant knowledge:"]
    for chunk in chunks:
        label = staleness_label(chunk.meta)
        prefix = f"{label} " if label else ""
        lines.append(f"- [{chunk.source}] {prefix}{chunk.content}")
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

    async def _embed_query(self, search_query: str) -> list[float]:
        cache_key = embedding_cache_key(search_query)
        cached = get_cached_embedding(cache_key)
        if cached is not None:
            return cached
        provider = get_embedding_provider()
        vector = await provider.embed_text(search_query)
        set_cached_embedding(cache_key, vector)
        return vector

    def _chunks_from_cache(self, rows: list[dict]) -> list[RAGChunk]:
        return [
            RAGChunk(
                id=row["id"],
                content=row["content"],
                source=row["source"],
                score=row["score"],
                doc_type=row.get("doc_type", "document"),
                meta=row.get("meta"),
            )
            for row in rows
        ]

    def _chunks_to_cache(self, chunks: list[RAGChunk]) -> list[dict]:
        return [
            {
                "id": c.id,
                "content": c.content,
                "source": c.source,
                "score": c.score,
                "doc_type": c.doc_type,
                "meta": c.meta,
            }
            for c in chunks
        ]

    async def _expand_parent_context(self, ranked: list[ScoredDocument]) -> list[ScoredDocument]:
        if not settings.rag_parent_expand_enabled:
            return ranked
        storage = await get_storage()
        expanded: list[ScoredDocument] = []
        seen_parents: set[str] = set()
        for item in ranked:
            meta = item.meta or {}
            if meta.get("type") != "filing":
                expanded.append(item)
                continue
            parent_id = meta.get("parent_id")
            chunk_index = meta.get("chunk_index", 0)
            if not parent_id or parent_id in seen_parents or chunk_index == 0:
                expanded.append(item)
                if parent_id:
                    seen_parents.add(parent_id)
                continue
            siblings = await storage.get_rag_parent_chunks(parent_id)
            header = siblings[0] if siblings else None
            expanded.append(enrich_filing_parent_context(item, header))
            seen_parents.add(parent_id)
        return expanded

    async def _apply_cross_encoder(
        self,
        query: str,
        ranked: list[ScoredDocument],
        *,
        preferred_types: list[str] | None,
        top_k: int,
    ) -> list[ScoredDocument]:
        if not should_use_cross_encoder(query, preferred_types):
            return ranked
        reranker = get_reranker_provider()
        if reranker is None:
            return ranked
        pool = ranked[: settings.rag_candidate_pool]
        docs = [
            {
                "chunk_id": item.chunk_id,
                "content": item.content,
                "source": item.source,
                "meta": item.meta,
                "final_score": item.final_score,
            }
            for item in pool
        ]
        reranked = await reranker.rerank(query, docs, top_k=top_k)
        by_id = {item.chunk_id: item for item in pool}
        merged: list[ScoredDocument] = []
        for doc in reranked:
            base = by_id.get(doc.get("chunk_id", ""))
            if not base:
                continue
            rerank_score = float(doc.get("rerank_score", base.final_score))
            blended = base.final_score * 0.4 + rerank_score * 0.6
            merged.append(
                ScoredDocument(
                    chunk_id=base.chunk_id,
                    content=base.content,
                    source=base.source,
                    meta=base.meta,
                    vector_score=base.vector_score,
                    keyword_score=base.keyword_score,
                    hybrid_score=base.hybrid_score,
                    final_score=blended,
                )
            )
        return merged or ranked[:top_k]

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[RAGChunk]:
        top_k = top_k or settings.rag_top_k
        try:
            await self.ensure_index()

            preferred_types = doc_types if doc_types is not None else infer_doc_types(query)
            search_query = rewrite_query(query, ticker)
            pool = settings.rag_candidate_pool

            cache_key = result_cache_key(
                query, top_k=top_k, ticker=ticker, doc_types=preferred_types
            )
            cached_rows = get_cached_results(cache_key)
            if cached_rows is not None:
                return self._chunks_from_cache(cached_rows)

            query_vec = await self._embed_query(search_query)
            storage = await get_storage()

            vector_hits = await self._vector_candidates(
                query_vec,
                pool=pool,
                ticker=ticker,
                doc_types=preferred_types,
            )

            vector_hits = apply_temporal_filter(vector_hits, query)
            vector_hits = apply_news_freshness_cutoff(vector_hits, query)

            if settings.rag_keyword_search_enabled and settings.rag_hybrid_search_enabled:
                keyword_ranked = await storage.keyword_search_rag(
                    query,
                    top_k=pool,
                    ticker=ticker,
                    doc_types=preferred_types,
                )
                keyword_ranked = apply_temporal_filter(keyword_ranked, query)
                keyword_ranked = apply_news_freshness_cutoff(keyword_ranked, query)
            else:
                corpus = await storage.list_rag_documents(ticker=ticker, doc_types=preferred_types)
                corpus = apply_temporal_filter(corpus, query)
                corpus = apply_news_freshness_cutoff(corpus, query)
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
                top_k=pool,
            )
            ranked = await self._expand_parent_context(ranked)
            ranked = await self._apply_cross_encoder(
                query, ranked, preferred_types=preferred_types, top_k=top_k
            )
            if len(ranked) > top_k:
                ranked = ranked[:top_k]

            chunks = [chunk_from_ranked(item, doc_type=(item.meta or {}).get("type")) for item in ranked]
            set_cached_results(cache_key, self._chunks_to_cache(chunks))
            return chunks
        except Exception as exc:
            logger.warning("rag_search_failed", error=str(exc), query=query[:120], ticker=ticker)
            if doc_types is not None:
                return []
            return self._keyword_fallback(query, top_k, ticker=ticker)

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
                        doc_type=(doc.get("meta") or {}).get("type", "playbook"),
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

    async def store_documents(self, documents: list[dict]) -> int:
        if not documents:
            return 0
        storage = await get_storage()
        docs = []
        for doc in documents:
            meta = dict(doc.get("meta") or {})
            meta.setdefault("type", "document")
            docs.append(
                {
                    "chunk_id": doc.get("chunk_id") or doc.get("id"),
                    "source": doc.get("source", "upload"),
                    "content": doc["content"],
                    "embedding": doc["embedding"],
                    "meta": meta,
                }
            )
        count = await storage.upsert_rag_documents(docs)
        from app.rag.cache import invalidate_rag_caches

        invalidate_rag_caches()
        self.mark_ready()
        return count

    async def embed_and_store(self, documents: list[dict]) -> int:
        from app.rag.pipeline import RAGIngestPipeline

        result = await RAGIngestPipeline(self).ingest(documents)
        return int(result["stored"])
