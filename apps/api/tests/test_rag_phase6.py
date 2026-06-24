"""Phase 6 RAG — Postgres keyword search and retrieval eval."""

import pytest

from app.db.storage import MemoryStorageBackend, get_storage
from app.rag.eval.runner import _retrieval_recall, load_golden_queries
from app.rag.service import RAGService


@pytest.mark.asyncio
async def test_keyword_search_rag_memory_backend():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-wash",
                "source": "tax-rules.md",
                "content": "Wash sale rule blocks repurchase within 30 days after a loss.",
                "embedding": [0.1] * 3,
                "meta": {"type": "playbook"},
            },
            {
                "chunk_id": "pb-sector",
                "source": "sector-rules.md",
                "content": "Technology sector exposure above 30% triggers caution.",
                "embedding": [0.2] * 3,
                "meta": {"type": "playbook"},
            },
        ]
    )

    hits = await store.keyword_search_rag("wash sale", top_k=2, doc_types=["playbook"])
    assert hits
    assert "wash sale" in hits[0]["content"].lower()


@pytest.mark.asyncio
async def test_rag_service_uses_keyword_search_path():
    storage = await get_storage()
    await storage.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-vix-rising",
                "source": "risk-playbook.md",
                "content": "When VIX is rising, reduce position size and avoid new tech adds.",
                "embedding": [0.9, 0.1, 0.0],
                "meta": {"type": "playbook", "title": "VIX"},
            }
        ]
    )
    RAGService.mark_ready()

    chunks = await RAGService().search("VIX rising rule", top_k=1, doc_types=["playbook"])
    assert chunks
    assert "VIX" in chunks[0].content


@pytest.mark.asyncio
async def test_retrieval_recall_golden_case():
    RAGService._seeded = False
    await RAGService().ensure_index()
    RAGService.mark_ready()

    case = next(c for c in load_golden_queries() if c["id"] == "wash-sale-playbook")
    result = await _retrieval_recall(case)
    assert result["passed"] is True
    assert not result.get("skipped")


@pytest.mark.asyncio
async def test_rag_chunk_metadata_in_to_dict():
    from app.rag.service import RAGChunk

    payload = RAGChunk(
        id="sec-nvda-1",
        content="Risk factors include supply chain concentration.",
        source="NVDA 10-K",
        score=0.91,
        doc_type="filing",
        meta={
            "type": "filing",
            "section": "Risk Factors",
            "filed_at": "2024-02-21",
            "url": "https://example.com/filing",
        },
    ).to_dict()
    assert payload["section"] == "Risk Factors"
    assert payload["filed_at"] == "2024-02-21"
    assert payload["url"] == "https://example.com/filing"
