"""Validate and normalize LLM narrative replies."""

from __future__ import annotations

import re

_TABLE_ROW = re.compile(r"^\s*\|")
_HEADER = re.compile(r"^#{1,6}\s")
_BULLET = re.compile(r"^[\-*•]\s")
_NUMBERED = re.compile(r"^\d+\.\s")


def validate_llm_reply(reply: str, *, max_words: int = 90) -> str:
    """Strip UI-duplicative markdown and cap length."""
    if not reply or not reply.strip():
        return ""

    cleaned_lines: list[str] = []
    in_table = False

    for line in reply.splitlines():
        stripped = line.strip()
        if not stripped:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            in_table = False
            continue
        if _TABLE_ROW.match(stripped):
            in_table = True
            continue
        if in_table:
            continue
        if _HEADER.match(stripped):
            continue
        if _BULLET.match(stripped) or _NUMBERED.match(stripped):
            continue
        if stripped.lower().startswith("snapshot") or stripped.lower().startswith("key factors"):
            continue
        cleaned_lines.append(line.rstrip())

    text = "\n".join(cleaned_lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)

    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip() + "…"

    return text


def inject_citation_markers(narrative: str, citation_count: int) -> str:
    """Append source markers when narrative mentions news but lacks citations."""
    if citation_count <= 0 or not narrative:
        return narrative
    if re.search(r"\[\d+\]", narrative):
        return narrative
    if re.search(r"\b(headlines?|news|report|article|source)\b", narrative, re.I):
        markers = " ".join(f"[{i}]" for i in range(1, min(citation_count, 3) + 1))
        return f"{narrative.rstrip()} {markers}"
    return narrative
