"""Read-only research-mode multi-tool retrieval (no execution path)."""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.rag.router import plan_query
from app.rag.service import RAGChunk
from app.rag.tool_routing import infer_rag_tools, infer_rag_tools_with_fallback
from app.rag.tools import RAGTools

logger = structlog.get_logger()

_BROADEN_HINTS = (
    "playbook",
    "risk",
    "filing",
    "regime",
    "news",
)


async def research_retrieve(
    message: str,
    *,
    ticker: str | None = None,
    top_k: int | None = None,
) -> tuple[list[RAGChunk], list[str], dict]:
    """Capped multi-round retrieval for deep research queries."""
    if not settings.rag_research_mode_enabled:
        tools = RAGTools()
        chunks, used, direct, plan = await tools.retrieve_for_message(
            message, ticker=ticker, top_k=top_k
        )
        return chunks, used, {"rounds": 1, "plan": plan.model_dump(), "direct": direct}

    tools = RAGTools()
    top_k = top_k or settings.rag_top_k
    merged: dict[str, RAGChunk] = {}
    tools_used: list[str] = []
    rounds: list[dict] = []

    query = message
    max_rounds = settings.rag_research_max_tool_rounds
    for round_idx in range(max_rounds):
        hinted = infer_rag_tools_with_fallback(query)
        plan = plan_query(query, tickers=[ticker] if ticker else None)
        if hinted:
            plan.use_rag = True
            plan.rag_tools = list(dict.fromkeys(hinted + plan.rag_tools))

        chunks, used, direct, _ = await tools.execute_plan(
            plan, query, ticker=ticker, top_k=top_k
        )
        for chunk in chunks:
            existing = merged.get(chunk.id)
            if not existing or chunk.score > existing.score:
                merged[chunk.id] = chunk
        tools_used.extend(used)
        rounds.append(
            {
                "round": round_idx + 1,
                "tools": used,
                "chunks": len(chunks),
            }
        )

        if len(merged) >= top_k:
            break
        if round_idx + 1 < max_rounds and len(chunks) < 2:
            query = f"{message} {' '.join(_BROADEN_HINTS)}"

    ranked = sorted(merged.values(), key=lambda c: c.score, reverse=True)[:top_k]
    logger.info(
        "research_retrieve_complete",
        rounds=len(rounds),
        chunks=len(ranked),
        tools=list(dict.fromkeys(tools_used)),
    )
    return ranked, list(dict.fromkeys(tools_used)), {"rounds": rounds}
