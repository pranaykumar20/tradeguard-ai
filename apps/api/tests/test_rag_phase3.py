"""Phase 3 RAG — smarter retrieval."""

from datetime import datetime, timezone

import pytest

from app.db.storage import MemoryStorageBackend
from app.rag.retrieval import (
    infer_doc_types,
    keyword_score,
    reciprocal_rank_fusion,
    recency_multiplier,
    rewrite_query,
)
from app.rag.service import RAGService


def test_rewrite_query_expands_vix():
    rewritten = rewrite_query("What happens when VIX is rising?")
    assert "volatility" in rewritten.lower()
    assert "VIX" in rewritten


def test_rewrite_query_expands_wash_sale():
    rewritten = rewrite_query("wash sale rules for NVDA")
    assert "wash sale" in rewritten.lower()
    assert "30 day" in rewritten.lower()


def test_infer_doc_types_playbook():
    assert infer_doc_types("What is the VIX rising rule?") == ["playbook"]


def test_infer_doc_types_filing():
    assert infer_doc_types("Show NVDA 10-K risk factors") == ["filing"]


def test_infer_doc_types_news():
    assert infer_doc_types("Latest NVDA news headlines today") == ["news"]


def test_keyword_score_prefers_exact_terms():
    high = keyword_score("wash sale", "Avoid wash sale within 30 days after a loss.")
    low = keyword_score("wash sale", "Technology sector exposure above 30%.")
    assert high > low


def test_recency_multiplier_boosts_recent_news():
    recent = recency_multiplier(
        {"type": "news", "published_at": datetime.now(timezone.utc).isoformat()}
    )
    old = recency_multiplier({"type": "news", "published_at": "2020-01-01T00:00:00Z"})
    assert recent > old


def test_reciprocal_rank_fusion():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert fused["b"] > fused["c"]
    assert fused["a"] > 0


@pytest.mark.asyncio
async def test_hybrid_search_finds_vix_playbook():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-vix",
                "source": "risk-playbook.md",
                "content": (
                    "Never add to a tech-heavy portfolio when QQQ is below its 50-day moving "
                    "average and VIX is rising. Reduce position size by 40%."
                ),
                "embedding": [0.1, 0.9, 0.0],
                "meta": {"type": "playbook", "title": "VIX regime"},
            },
            {
                "chunk_id": "pb-sector",
                "source": "sector-rules.md",
                "content": "Technology sector exposure above 30% triggers CAUTION.",
                "embedding": [0.9, 0.1, 0.0],
                "meta": {"type": "playbook", "title": "Sector cap"},
            },
            {
                "chunk_id": "news-old",
                "source": "NVDA news",
                "content": "NVDA announced a new chip.",
                "embedding": [0.5, 0.5, 0.0],
                "meta": {
                    "type": "news",
                    "ticker": "NVDA",
                    "published_at": "2020-01-01T00:00:00Z",
                },
            },
        ]
    )

    service = RAGService()
    service.mark_ready()
    chunks = await service.search("VIX rising — should I add tech?", top_k=1)
    assert chunks
    assert "VIX" in chunks[0].content


@pytest.mark.asyncio
async def test_hybrid_search_finds_wash_sale_playbook():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-wash",
                "source": "tax-rules.md",
                "content": (
                    "Avoid repurchasing the same ticker within 30 days after a loss-generating "
                    "sale if you intend to claim the loss for taxes. Wash sale risk flagged."
                ),
                "embedding": [0.2, 0.2, 0.9],
                "meta": {"type": "playbook", "title": "Wash sale window"},
            },
            {
                "chunk_id": "pb-vix",
                "source": "risk-playbook.md",
                "content": "Reduce position size when VIX is rising.",
                "embedding": [0.9, 0.1, 0.0],
                "meta": {"type": "playbook", "title": "VIX regime"},
            },
        ]
    )

    service = RAGService()
    service.mark_ready()
    chunks = await service.search("What is the wash sale rule?", top_k=1)
    assert chunks
    assert "wash sale" in chunks[0].content.lower() or "30 days" in chunks[0].content.lower()


@pytest.mark.asyncio
async def test_type_routing_limits_to_playbooks():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-1",
                "source": "risk-playbook.md",
                "content": "Daily loss circuit breaker halts trading.",
                "embedding": [0.1, 0.9, 0.0],
                "meta": {"type": "playbook"},
            },
            {
                "chunk_id": "news-1",
                "source": "NVDA news",
                "content": "Daily loss circuit breaker mentioned in headline.",
                "embedding": [0.9, 0.9, 0.0],
                "meta": {
                    "type": "news",
                    "ticker": "NVDA",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]
    )

    service = RAGService()
    service.mark_ready()
    chunks = await service.search("daily loss circuit breaker rule", top_k=1)
    assert chunks
    assert "circuit breaker" in chunks[0].content.lower()
    assert chunks[0].source.endswith(".md")
