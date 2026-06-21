"""Load risk playbooks from docs/playbooks/*.md."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from app.core.config import settings

logger = structlog.get_logger()

_BUILTIN_PLAYBOOKS = [
    {
        "chunk_id": "risk-001",
        "source": "risk-playbook.md",
        "content": (
            "Never add to a tech-heavy portfolio when QQQ is below its 50-day moving average "
            "and VIX is rising. Reduce position size by 40% in high-volatility regimes."
        ),
    },
    {
        "chunk_id": "risk-002",
        "source": "risk-playbook.md",
        "content": (
            "Single-name concentration above 20% requires explicit user approval. "
            "NVDA, META, MSFT combined with QQQ creates hidden correlation risk."
        ),
    },
    {
        "chunk_id": "risk-003",
        "source": "risk-playbook.md",
        "content": (
            "No market orders on volatile tickers. Use limit orders with defined stop loss. "
            "Do not trade in the first 10 minutes after market open."
        ),
    },
    {
        "chunk_id": "risk-004",
        "source": "risk-playbook.md",
        "content": (
            "Daily loss circuit breaker: halt all new trades when daily P&L exceeds the "
            "configured loss limit. Review open positions before resuming."
        ),
    },
    {
        "chunk_id": "risk-005",
        "source": "position-sizing.md",
        "content": (
            "Maximum trade size is $250 in Phase 1. Scale into positions over multiple days "
            "rather than adding full size in one order when RSI is above 70."
        ),
    },
    {
        "chunk_id": "risk-006",
        "source": "sector-rules.md",
        "content": (
            "Technology sector exposure above 30% triggers CAUTION on new tech buys. "
            "Consider diversifying into healthcare or consumer names before adding NVDA or META."
        ),
    },
    {
        "chunk_id": "risk-007",
        "source": "options-policy.md",
        "content": (
            "Options are blocked in Phase 1 without explicit manual approval. "
            "Stocks and ETFs only on the allowed ticker list."
        ),
    },
]


def _playbook_search_paths() -> list[Path]:
    """Candidate playbook dirs — monorepo, Docker (/app), and explicit override."""
    paths: list[Path] = []
    if settings.rag_playbooks_dir:
        paths.append(Path(settings.rag_playbooks_dir))

    module_dir = Path(__file__).resolve().parent
    paths.append(module_dir / "playbooks")
    if len(module_dir.parents) > 2:
        paths.append(module_dir.parents[2] / "playbooks")

    seen: set[Path] = set()
    for ancestor in module_dir.parents:
        candidate = ancestor / "docs" / "playbooks"
        if candidate not in seen:
            paths.append(candidate)
            seen.add(candidate)

    return paths


def default_playbooks_dir() -> Path:
    for path in _playbook_search_paths():
        if path.is_dir():
            return path
    # Missing dir — load_playbook_documents() uses builtin fallback
    return _playbook_search_paths()[0]


def _parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "overview"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_title, body))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if line.startswith("# "):
            continue
        current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_title, body))
    return sections


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def load_playbook_documents(playbooks_dir: Path | None = None) -> list[dict]:
    directory = playbooks_dir or default_playbooks_dir()
    if not directory.is_dir():
        logger.warning("playbooks_dir_missing", path=str(directory))
        return _builtin_playbook_documents()

    documents: list[dict] = []
    for md_file in sorted(directory.glob("*.md")):
        sections = _parse_markdown_sections(md_file.read_text(encoding="utf-8"))
        for index, (title, content) in enumerate(sections, start=1):
            chunk_id = f"playbook-{_slug(md_file.stem)}-{_slug(title)}-{index:02d}"
            documents.append(
                {
                    "chunk_id": chunk_id,
                    "source": md_file.name,
                    "content": content,
                    "meta": {
                        "type": "playbook",
                        "title": title,
                        "file": md_file.name,
                        "visibility": "global",
                    },
                }
            )

    if not documents:
        logger.warning("playbooks_dir_empty", path=str(directory))
        return _builtin_playbook_documents()

    logger.info("playbooks_loaded", path=str(directory), chunks=len(documents))
    return documents


def _builtin_playbook_documents() -> list[dict]:
    return [
        {
            "chunk_id": doc["chunk_id"],
            "source": doc["source"],
            "content": doc["content"],
            "meta": {"type": "playbook", "title": doc["chunk_id"], "file": doc["source"], "visibility": "global"},
        }
        for doc in _BUILTIN_PLAYBOOKS
    ]


def playbook_fallback_chunks() -> list[dict]:
    """Keyword fallback corpus — same content as indexed playbooks."""
    return load_playbook_documents()
