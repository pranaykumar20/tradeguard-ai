"""Phase 5 P0 — ingestion pipeline, chunkers, content-hash dedupe."""

import pytest

from app.rag.chunkers.news import chunk_news_documents
from app.rag.chunkers.playbook import chunk_playbook_documents
from app.rag.pipeline import RAGIngestPipeline, content_hash, normalize_document
from app.providers.embeddings.factory import embedding_model_for_doc_type


def test_content_hash_stable():
    assert content_hash("hello") == content_hash("hello")
    assert content_hash("hello") != content_hash("world")


def test_normalize_document_sets_defaults():
    doc = normalize_document(
        {"chunk_id": "test-1", "content": "Rule text", "meta": {"type": "playbook"}}
    )
    assert doc["meta"]["visibility"] == "global"
    assert doc["meta"]["embedding_version"] >= 1


def test_playbook_chunker_splits_long_sections():
    long_body = " ".join(["word"] * 200)
    docs = chunk_playbook_documents(
        [
            {
                "chunk_id": "playbook-test-section-01",
                "source": "test.md",
                "content": long_body,
                "meta": {"type": "playbook"},
            }
        ]
    )
    assert len(docs) > 1
    assert all("-part-" in d["chunk_id"] for d in docs)


def test_news_chunker_enriches_summary():
    docs = chunk_news_documents(
        [
            {
                "chunk_id": "news-nvda-abc",
                "source": "NVDA news",
                "content": "NVDA beats estimates",
                "meta": {
                    "type": "news",
                    "title": "NVDA beats estimates",
                    "summary": "Revenue up 20% year over year.",
                    "source_name": "MockWire",
                },
            }
        ]
    )
    assert len(docs) == 1
    assert "Revenue up 20%" in docs[0]["content"]
    assert "MockWire" in docs[0]["content"]


def test_embedding_model_for_doc_type():
    assert embedding_model_for_doc_type("playbook") == embedding_model_for_doc_type("news")
    assert embedding_model_for_doc_type("filing")  # defaults to main model when filing override unset


@pytest.mark.asyncio
async def test_pipeline_skips_unchanged_content(monkeypatch):
    from app.db.storage import MemoryStorageBackend

    storage = MemoryStorageBackend()
    await storage.init()

    async def fake_get_storage():
        return storage

    digest = content_hash("unchanged playbook rule")
    await storage.upsert_rag_documents(
        [
            {
                "chunk_id": "playbook-test-01",
                "source": "test.md",
                "content": "unchanged playbook rule",
                "embedding": [0.1] * 1536,
                "meta": {"type": "playbook", "content_hash": digest},
            }
        ]
    )

    monkeypatch.setattr("app.rag.pipeline.get_storage", fake_get_storage)
    monkeypatch.setattr("app.rag.pipeline.settings.rag_content_hash_enabled", True)

    pipeline = RAGIngestPipeline()
    result = await pipeline.ingest(
        [
            {
                "chunk_id": "playbook-test-01",
                "source": "test.md",
                "content": "unchanged playbook rule",
                "meta": {"type": "playbook"},
            }
        ]
    )
    assert result["stored"] == 0
    assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_indexer_refresh_source_playbooks(monkeypatch, tmp_path):
    from app.rag.indexer import RAGIndexer

    md = tmp_path / "risk-playbook.md"
    md.write_text("## Rule\n\nAlways use limit orders.\n", encoding="utf-8")

    stored: list[int] = []

    class FakePipeline:
        async def ingest(self, documents, *, skip_chunking=False):
            stored.append(len(documents))
            return {"stored": len(documents), "skipped": 0, "chunks": len(documents)}

    monkeypatch.setattr("app.rag.indexer.settings.rag_playbooks_dir", str(tmp_path))
    monkeypatch.setattr("app.rag.indexer.RAGIngestPipeline", lambda: FakePipeline())

    result = await RAGIndexer().refresh_source("playbooks")
    assert result["source"] == "playbooks"
    assert result["stored"] == 1
    assert stored == [1]
