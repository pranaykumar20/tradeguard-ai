"""Phase 7/8 RAG — quality, freshness, cache, research mode."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.db.storage import MemoryStorageBackend
from app.rag.cache import (
    embedding_cache_key,
    get_cached_embedding,
    invalidate_rag_caches,
    set_cached_embedding,
)
from app.rag.eval.runner import check_rag_drift, record_negative_rag_feedback
from app.rag.indexers.regime_snapshot import build_regime_snapshot_document
from app.rag.retrieval import (
    ScoredDocument,
    apply_news_freshness_cutoff,
    enrich_filing_parent_context,
    is_today_news_query,
    staleness_label,
)
from app.rag.service import RAGService, format_chunks_for_context
from app.rag.tool_routing import classify_rag_tools_fallback, infer_rag_tools_with_fallback


def test_is_today_news_query():
    assert is_today_news_query("What is NVDA news today?")
    assert not is_today_news_query("NVDA 10-K risk factors")


def test_apply_news_freshness_cutoff():
    now = datetime.now(timezone.utc)
    fresh = {
        "chunk_id": "news-fresh",
        "content": "NVDA beats earnings",
        "meta": {"type": "news", "published_at": now.isoformat()},
    }
    stale = {
        "chunk_id": "news-stale",
        "content": "Old headline",
        "meta": {
            "type": "news",
            "published_at": (now - timedelta(days=30)).isoformat(),
        },
    }
    playbook = {
        "chunk_id": "pb-1",
        "content": "Wash sale rule",
        "meta": {"type": "playbook"},
    }
    filtered = apply_news_freshness_cutoff([fresh, stale, playbook], "NVDA news today")
    ids = {doc["chunk_id"] for doc in filtered}
    assert "news-fresh" in ids
    assert "news-stale" not in ids
    assert "pb-1" in ids


def test_staleness_label_for_old_filing():
    old_date = (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()
    label = staleness_label({"type": "filing", "filed_at": old_date})
    assert label.startswith("[STALE: filed")


def test_enrich_filing_parent_context():
    item = ScoredDocument(
        chunk_id="sec-nvda-part-02",
        content="Supply chain concentration risk.",
        source="NVDA 10-K",
        meta={"type": "filing", "section": "Risk Factors", "chunk_index": 2},
        vector_score=0.8,
        keyword_score=1.0,
        hybrid_score=0.7,
        final_score=0.75,
    )
    header = {
        "content": "Risk Factors — NVIDIA Corporation",
        "meta": {"section": "Risk Factors"},
    }
    enriched = enrich_filing_parent_context(item, header)
    assert "Risk Factors" in enriched.content
    assert "Supply chain" in enriched.content


def test_classifier_fallback():
    tools = classify_rag_tools_fallback("What is the macro regime right now?")
    assert "search_regime" in tools
    assert infer_rag_tools_with_fallback("random gibberish xyz") == ["search_playbooks"]


def test_embedding_cache_roundtrip():
    invalidate_rag_caches()
    key = embedding_cache_key("wash sale rule")
    assert get_cached_embedding(key) is None
    set_cached_embedding(key, [0.1, 0.2, 0.3])
    assert get_cached_embedding(key) == [0.1, 0.2, 0.3]


def test_regime_snapshot_document():
    doc = build_regime_snapshot_document(
        {"regime": "risk_off", "label": "Risk-Off", "risk_score_adjustment": -5, "signals": {}}
    )
    assert doc["meta"]["type"] == "regime_snapshot"
    assert "Risk-Off" in doc["content"]


@pytest.mark.asyncio
async def test_delete_stale_rag_news():
    store = MemoryStorageBackend()
    await store.init()
    now = datetime.now(timezone.utc)
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "news-old",
                "source": "news",
                "content": "old",
                "embedding": [0.1] * settings.embedding_dimensions,
                "meta": {
                    "type": "news",
                    "published_at": (now - timedelta(days=40)).isoformat(),
                },
            },
            {
                "chunk_id": "news-new",
                "source": "news",
                "content": "new",
                "embedding": [0.2] * settings.embedding_dimensions,
                "meta": {"type": "news", "published_at": now.isoformat()},
            },
        ]
    )
    deleted = await store.delete_stale_rag_news(older_than_days=30)
    assert deleted == 1
    raw = await store.list_rag_documents_raw()
    assert len(raw) == 1
    assert raw[0]["chunk_id"] == "news-new"


@pytest.mark.asyncio
async def test_parent_chunk_lookup():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "sec-nvda-10k-risk-01",
                "source": "NVDA 10-K",
                "content": "Risk Factors header",
                "embedding": [0.1] * settings.embedding_dimensions,
                "meta": {"type": "filing", "parent_id": "sec-nvda-10k-risk", "chunk_index": 0},
            },
            {
                "chunk_id": "sec-nvda-10k-risk-02",
                "source": "NVDA 10-K",
                "content": "Supply chain risk detail",
                "embedding": [0.2] * settings.embedding_dimensions,
                "meta": {"type": "filing", "parent_id": "sec-nvda-10k-risk", "chunk_index": 1},
            },
        ]
    )
    siblings = await store.get_rag_parent_chunks("sec-nvda-10k-risk")
    assert len(siblings) == 2
    assert siblings[0]["meta"]["chunk_index"] == 0


@pytest.mark.asyncio
async def test_format_chunks_includes_staleness():
    from app.rag.service import RAGChunk

    old_date = (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()
    chunk = RAGChunk(
        id="f1",
        content="Old risk factor",
        source="NVDA 10-K",
        score=0.9,
        meta={"type": "filing", "filed_at": old_date},
    )
    text = format_chunks_for_context([chunk])
    assert "[STALE: filed" in text


@pytest.mark.asyncio
async def test_drift_baseline_set():
    from app.db.storage import get_storage

    storage = await get_storage()
    await storage.set_app_state("rag_eval_baseline", None)
    result = await check_rag_drift({"retrieval_recall_pct": 88.0})
    assert result.get("baseline_set") is True


@pytest.mark.asyncio
async def test_negative_feedback_recorded():
    from app.db.storage import get_storage

    await record_negative_rag_feedback(
        session_id="sess-1",
        rag_chunk_ids=["chunk-a", "chunk-b"],
        comment="wrong filing",
    )
    storage = await get_storage()
    state = await storage.get_app_state("rag_negative_feedback")
    assert state
    assert state["entries"][-1]["rag_chunk_ids"] == ["chunk-a", "chunk-b"]


@pytest.mark.asyncio
async def test_search_regime_doc_type():
    from app.db.storage import get_storage

    storage = await get_storage()
    await storage.upsert_rag_documents(
        [
            {
                "chunk_id": "regime-today",
                "source": "Macro regime snapshot",
                "content": "Market regime: Risk-Off with elevated volatility.",
                "embedding": [0.5, 0.5, 0.0],
                "meta": {
                    "type": "regime_snapshot",
                    "as_of": datetime.now(timezone.utc).isoformat(),
                },
            }
        ]
    )
    RAGService.mark_ready()
    chunks = await RAGService().search("macro regime environment", top_k=1, doc_types=["regime_snapshot"])
    assert chunks
    assert "regime" in chunks[0].content.lower()
