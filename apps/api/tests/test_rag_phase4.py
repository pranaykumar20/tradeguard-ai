"""Phase 4 RAG — agentic tools and journal namespace."""

import pytest

from app.core.user_context import user_scope
from app.db.storage import _rag_visible_to_user, get_storage
from app.rag.journal_index import build_journal_document, index_user_journal
from app.rag.tools import RAGTools, infer_rag_tools
from app.rag.service import RAGService


def test_infer_rag_tools_filing_only():
    tools = infer_rag_tools("What are NVDA 10-K risk factors?")
    assert tools == ["search_filings"]


def test_infer_rag_tools_journal_only():
    tools = infer_rag_tools("What happened last time I tried to buy NVDA?")
    assert "search_journal" in tools


def test_infer_rag_tools_playbook_on_trade_question():
    tools = infer_rag_tools("Should I buy more NVDA today?")
    assert tools == ["search_playbooks"]


def test_infer_rag_tools_empty_for_generic():
    tools = infer_rag_tools("Hello")
    assert tools == []


def test_build_journal_document_filled_trade():
    doc = build_journal_document(
        {
            "id": "t1",
            "user_id": "user-a",
            "ticker": "NVDA",
            "side": "buy",
            "status": "filled",
            "verdict": "CAUTION",
            "reason": "Tech exposure high",
            "pnl": -12.5,
        },
        user_id="user-a",
    )
    assert doc is not None
    assert doc["meta"]["type"] == "journal"
    assert doc["meta"]["user_id"] == "user-a"
    assert "NVDA" in doc["content"]


def test_rag_visible_to_user_scopes_journal():
    assert _rag_visible_to_user({"type": "journal", "user_id": "a"}, "a") is True
    assert _rag_visible_to_user({"type": "journal", "user_id": "a"}, "b") is False
    assert _rag_visible_to_user({"type": "playbook"}, "b") is True


@pytest.mark.asyncio
async def test_journal_search_isolated_per_user():
    storage = await get_storage()

    async def seed_user(user_id: str, trade_id: str, content: str):
        async with user_scope(user_id):
            await storage.upsert_rag_documents(
                [
                    {
                        "chunk_id": f"journal-{user_id}-{trade_id}",
                        "source": "Trade journal — NVDA buy",
                        "content": content,
                        "embedding": [0.2, 0.8, 0.1],
                        "meta": {
                            "type": "journal",
                            "user_id": user_id,
                            "ticker": "NVDA",
                        },
                    }
                ]
            )

    await seed_user("user-a", "t1", "NVDA buy blocked due to tech exposure for user A")
    await seed_user("user-b", "t2", "NVDA buy blocked due to tech exposure for user B")

    service = RAGService()
    RAGService.mark_ready()

    async with user_scope("user-a"):
        hits = await service.search(
            "last time NVDA blocked tech exposure",
            top_k=3,
            doc_types=["journal"],
        )
    assert len(hits) == 1
    assert "user A" in hits[0].content


@pytest.mark.asyncio
async def test_agentic_tools_retrieve_filings_not_playbooks():
    storage = await get_storage()
    await storage.upsert_rag_documents(
        [
            {
                "chunk_id": "pb-1",
                "source": "risk-playbook.md",
                "content": "VIX rising reduces position size.",
                "embedding": [0.9, 0.1, 0.0],
                "meta": {"type": "playbook"},
            },
            {
                "chunk_id": "fil-1",
                "source": "NVDA 10-K Risk Factors",
                "content": "Export controls on advanced GPU sales to China.",
                "embedding": [0.1, 0.9, 0.0],
                "meta": {"type": "filing", "ticker": "NVDA"},
            },
        ]
    )

    tools = RAGTools()
    RAGService.mark_ready()
    chunks, used, _, _ = await tools.retrieve_for_message(
        "NVDA 10-K risk factors export controls",
        ticker="NVDA",
        top_k=2,
    )
    assert used == ["search_filings"]
    assert chunks
    assert all("10-K" in c.source or "export" in c.content.lower() for c in chunks)


@pytest.mark.asyncio
async def test_index_user_journal_from_trades():
    storage = await get_storage()
    async with user_scope("user-a"):
        await storage.create_paper_trade(
            {
                "ticker": "NVDA",
                "side": "buy",
                "quantity": 1,
                "limit_price": 100,
                "status": "rejected",
                "verdict": "BLOCK",
                "reason": "Tech exposure exceeded",
            }
        )
        count = await index_user_journal()
    assert count == 1
