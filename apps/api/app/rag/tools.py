"""Agentic RAG tools — intent-based retrieval."""

from __future__ import annotations

import asyncio
import re

import structlog

from app.core.config import settings
from app.rag.service import RAGChunk, RAGService

logger = structlog.get_logger()

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

    if not tools:
        if TICKER_PATTERN.search(message) and any(
            word in q for word in ("buy", "sell", "add", "trade", "analyze")
        ):
            return ["search_playbooks"]
        return []

    return list(dict.fromkeys(tools))


class RAGTools:
    def __init__(self):
        self.rag = RAGService()

    async def search_playbooks(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["playbook"],
        )

    async def search_filings(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["filing"],
        )

    async def search_journal(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["journal"],
        )

    async def retrieve_for_message(
        self,
        message: str,
        *,
        ticker: str | None = None,
        top_k: int | None = None,
    ) -> tuple[list[RAGChunk], list[str]]:
        """Run agentic tool routing; return merged chunks and tools used."""
        top_k = top_k or settings.rag_top_k
        tool_names = infer_rag_tools(message)

        if not tool_names:
            return [], []

        per_tool_k = max(1, top_k // len(tool_names))
        tasks = []
        for name in tool_names:
            if name == "search_playbooks":
                tasks.append(self.search_playbooks(message, ticker=ticker, top_k=per_tool_k))
            elif name == "search_filings":
                tasks.append(self.search_filings(message, ticker=ticker, top_k=per_tool_k))
            elif name == "search_journal":
                tasks.append(self.search_journal(message, ticker=ticker, top_k=per_tool_k))

        results = await asyncio.gather(*tasks)
        merged: dict[str, RAGChunk] = {}
        for chunks in results:
            for chunk in chunks:
                existing = merged.get(chunk.id)
                if not existing or chunk.score > existing.score:
                    merged[chunk.id] = chunk

        ranked = sorted(merged.values(), key=lambda c: c.score, reverse=True)[:top_k]
        logger.info(
            "rag_tools_invoked",
            tools=tool_names,
            chunks=len(ranked),
            ticker=ticker,
        )
        return ranked, tool_names
