"""RAG document types and metadata conventions."""

from __future__ import annotations

from typing import Literal

RAG_DOC_TYPES = frozenset(
    {
        "playbook",
        "filing",
        "news",
        "journal",
        "analysis_snapshot",
        "ml_run",
        "regime_snapshot",
        "trade_note",
        "document",
    }
)

RAG_SOURCES = frozenset({"playbooks", "filings", "news", "journal", "all"})

RagSource = Literal["playbooks", "filings", "news", "journal", "all"]
RagDocType = Literal[
    "playbook",
    "filing",
    "news",
    "journal",
    "analysis_snapshot",
    "ml_run",
    "regime_snapshot",
    "trade_note",
    "document",
]

RAG_VISIBILITY = Literal["global", "tenant", "user"]

DEFAULT_EMBEDDING_VERSION = 1
