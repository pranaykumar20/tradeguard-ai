"""Build journal post-mortem documents for per-user RAG."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.core.user_context import get_current_user_id
from app.db.storage import get_storage

logger = structlog.get_logger()


def build_journal_document(trade: dict, user_id: str | None = None) -> dict | None:
    status = trade.get("status", "")
    if status not in {"filled", "rejected"}:
        return None

    uid = user_id or trade.get("user_id") or get_current_user_id()
    ticker = str(trade.get("ticker", "")).upper()
    side = trade.get("side", "buy")
    verdict = trade.get("verdict", "UNKNOWN")
    reason = (trade.get("reason") or "").strip()
    pnl = trade.get("pnl")
    trade_id = trade.get("id", "")

    outcome = f"Outcome PnL ${pnl:.2f}." if pnl is not None else "Trade closed."
    if status == "rejected":
        outcome = f"Trade rejected — {reason or 'risk engine blocked'}."

    content = (
        f"{ticker} {side} {status} with verdict {verdict}. "
        f"{reason + '. ' if reason else ''}{outcome} "
        f"Review before repeating similar {ticker} trades."
    )

    created_at = trade.get("created_at")
    if isinstance(created_at, datetime):
        closed_at = created_at.isoformat()
    else:
        closed_at = str(created_at) if created_at else datetime.now(timezone.utc).isoformat()

    return {
        "chunk_id": f"journal-{uid}-{trade_id}",
        "source": f"Trade journal — {ticker} {side}",
        "content": content,
        "meta": {
            "type": "journal",
            "user_id": uid,
            "ticker": ticker,
            "trade_id": trade_id,
            "status": status,
            "verdict": verdict,
            "pnl": pnl,
            "closed_at": closed_at,
        },
    }


async def index_user_journal(user_id: str | None = None) -> int:
    from app.rag.service import RAGService

    uid = user_id or get_current_user_id()
    storage = await get_storage()
    trades = await storage.list_paper_trades(limit=500)

    documents = []
    for trade in trades:
        if trade.get("user_id", uid) != uid:
            continue
        doc = build_journal_document(trade, user_id=uid)
        if doc:
            documents.append(doc)

    if not documents:
        return 0

    rag = RAGService()
    count = await rag.embed_and_store(documents)
    logger.info("rag_journal_indexed", user_id=uid, chunks=count)
    return count
