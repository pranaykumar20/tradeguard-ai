"""Query routing — decide RAG vs direct API calls per message."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.intent import PORTFOLIO_PATTERN
from app.agents.tickers import extract_tickers, is_price_query
from app.core.config import settings
from app.rag.retrieval import parse_temporal_window
from app.rag.tool_routing import infer_rag_tools, infer_rag_tools_with_fallback

Freshness = Literal["live", "recent", "historical"]

TRADE_HISTORY_HINTS = (
    "my trades",
    "my trade",
    "paper trade",
    "past orders",
    "trade history",
    "how many trades",
    "win rate",
    "recent trades",
)

ANALYSIS_RUN_HINTS = (
    "run analysis",
    "analyze ",
    "full analysis",
    "score breakdown",
    "setup score",
)

RISK_CHECK_HINTS = (
    "check risk",
    "risk limit",
    "would i be blocked",
    "can i buy",
    "can i sell",
    "preview trade",
)


class QueryPlan(BaseModel):
    use_rag: bool = True
    rag_tools: list[str] = Field(default_factory=list)
    direct_calls: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    freshness: Freshness = "recent"


def plan_query(message: str, tickers: list[str] | None = None) -> QueryPlan:
    """Rules-first router: live/computed data via direct calls; knowledge via RAG."""
    if not settings.rag_router_enabled:
        resolved = tickers or extract_tickers(message)
        return QueryPlan(
            use_rag=True,
            rag_tools=infer_rag_tools(message) or ["search_playbooks"],
            tickers=resolved,
            freshness="recent",
        )

    resolved = tickers or extract_tickers(message)
    primary = resolved[0] if resolved else None
    q = message.lower()
    direct: list[str] = []

    if is_price_query(message) or re.search(r"\b(quote|trading at)\b", q):
        if primary:
            direct.append("get_quote")

    if PORTFOLIO_PATTERN.search(message) or re.search(
        r"\b(exposure|allocation|holdings|portfolio value)\b", q
    ):
        direct.append("portfolio_snapshot")

    if any(hint in q for hint in TRADE_HISTORY_HINTS):
        direct.append("query_trades")

    if any(hint in q for hint in ANALYSIS_RUN_HINTS) and primary:
        direct.append("run_ticker_analysis")

    if (
        any(hint in q for hint in RISK_CHECK_HINTS)
        or re.search(r"\b(buy|sell|purchase|add)\b", q)
    ) and primary:
        if "check_risk_limits" not in direct:
            direct.append("check_risk_limits")

    if re.search(r"\b(model auc|ml status|model version)\b", q):
        direct.append("ml_status")

    rag_tools = infer_rag_tools_with_fallback(message)
    use_rag = bool(rag_tools)

    # Pure live price queries should not retrieve stale chunks
    if direct == ["get_quote"] and not rag_tools:
        use_rag = False

    if not use_rag and not direct:
        use_rag = True
        rag_tools = ["search_playbooks"]

    freshness: Freshness = "live" if "get_quote" in direct else "recent"
    if parse_temporal_window(message):
        freshness = "historical"

    return QueryPlan(
        use_rag=use_rag,
        rag_tools=rag_tools if use_rag else [],
        direct_calls=list(dict.fromkeys(direct)),
        tickers=resolved,
        freshness=freshness,
    )
