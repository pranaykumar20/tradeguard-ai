"""Phase 1 RAG — retrieval foundations."""

import pytest

from app.db.storage import MemoryStorageBackend, _rag_matches_ticker
from app.rag.service import RAGService, format_chunks_for_context


def test_rag_matches_ticker_playbook_always_included():
    assert _rag_matches_ticker({"type": "playbook"}, "NVDA") is True


def test_rag_matches_ticker_filing_filtered():
    assert _rag_matches_ticker({"type": "filing", "ticker": "NVDA"}, "NVDA") is True
    assert _rag_matches_ticker({"type": "filing", "ticker": "MSFT"}, "NVDA") is False


def test_rag_matches_ticker_no_filter():
    assert _rag_matches_ticker({"type": "filing", "ticker": "MSFT"}, None) is True


def test_format_chunks_for_context():
    from app.rag.service import RAGChunk

    chunks = [
        RAGChunk(id="a", content="Rule one", source="playbook.md", score=0.9),
        RAGChunk(id="b", content="Rule two", source="sector-rules.md", score=0.8),
    ]
    text = format_chunks_for_context(chunks)
    assert "Relevant knowledge:" in text
    assert "[playbook.md] Rule one" in text
    assert "[sector-rules.md] Rule two" in text


@pytest.mark.asyncio
async def test_memory_storage_ticker_filter():
    store = MemoryStorageBackend()
    await store.init()
    await store.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-1",
                "source": "playbook",
                "content": "Always use limit orders",
                "embedding": [1.0, 0.0, 0.0],
                "meta": {"type": "playbook"},
            },
            {
                "chunk_id": "nvda-1",
                "source": "NVDA 10-K",
                "content": "NVDA GPU concentration risk",
                "embedding": [0.9, 0.1, 0.0],
                "meta": {"type": "filing", "ticker": "NVDA"},
            },
            {
                "chunk_id": "msft-1",
                "source": "MSFT 10-K",
                "content": "MSFT cloud growth",
                "embedding": [0.8, 0.2, 0.0],
                "meta": {"type": "filing", "ticker": "MSFT"},
            },
        ]
    )
    hits = await store.search_rag([1.0, 0.0, 0.0], top_k=5, ticker="NVDA")
    chunk_ids = {h["chunk_id"] for h in hits}
    assert "pb-1" in chunk_ids
    assert "nvda-1" in chunk_ids
    assert "msft-1" not in chunk_ids


@pytest.mark.asyncio
async def test_rag_service_search_with_ticker(monkeypatch):
    monkeypatch.setattr("app.rag.service.RAGService._seeded", True)
    service = RAGService()
    chunks = await service.search("concentration risk", top_k=2, ticker="NVDA")
    assert len(chunks) <= 2
    assert all(isinstance(c.score, float) for c in chunks)


@pytest.mark.asyncio
async def test_rag_chunk_to_dict():
    from app.rag.service import RAGChunk

    chunk = RAGChunk(id="x", content="test", source="src", score=0.87654)
    d = chunk.to_dict()
    assert d["score"] == 0.8765
    assert d["source"] == "src"
