"""RAG tool hint matching — shared by router and RAGTools."""

from __future__ import annotations

import re

from app.core.config import settings

PLAYBOOK_TOOL_HINTS = (
    "rule",
    "playbook",
    "guardrail",
    "limit",
    "vix",
    "exposure",
    "sector",
    "options",
    "wash sale",
    "circuit breaker",
    "position size",
    "should i buy",
    "should i sell",
)

FILING_TOOL_HINTS = (
    "10-k",
    "10k",
    "10-q",
    "sec",
    "filing",
    "fundamental",
    "risk factor",
    "md&a",
    "annual report",
    "earnings report",
    "edgar",
)

JOURNAL_TOOL_HINTS = (
    "journal",
    "past trade",
    "previous trade",
    "last time",
    "history",
    "post-mortem",
    "postmortem",
    "mistake",
    "repeat",
    "before",
    "lost money",
    "blocked before",
)

ANALYSIS_HISTORY_HINTS = (
    "what did we think",
    "our view",
    "analysis history",
    "previous analysis",
    "last analysis",
    "what was the verdict",
    "composite score",
)

ML_RUN_HINTS = (
    "model version",
    "model auc",
    "retrain",
    "feature importance",
    "ml run",
    "model deployed",
    "walk-forward",
)

TICKER_PATTERN = re.compile(r"\b(NVDA|MSFT|META|TSLA|QQQ|GBTC|AAPL|SPY|SMH)\b", re.I)


def infer_rag_tools(message: str) -> list[str]:
    if not settings.rag_agentic_enabled:
        return ["search_playbooks"]

    q = message.lower()
    tools: list[str] = []
    if any(hint in q for hint in PLAYBOOK_TOOL_HINTS):
        tools.append("search_playbooks")
    if any(hint in q for hint in FILING_TOOL_HINTS):
        tools.append("search_filings")
    if any(hint in q for hint in JOURNAL_TOOL_HINTS):
        tools.append("search_journal")
    if any(hint in q for hint in ANALYSIS_HISTORY_HINTS):
        tools.append("search_analysis_history")
    if any(hint in q for hint in ML_RUN_HINTS):
        tools.append("search_ml_runs")

    if not tools:
        if TICKER_PATTERN.search(message) and any(
            word in q for word in ("buy", "sell", "add", "trade", "analyze")
        ):
            return ["search_playbooks"]
        return []

    return list(dict.fromkeys(tools))
