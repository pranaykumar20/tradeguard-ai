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


_CITATION_MARKER = re.compile(r"\[(\d+)\]")


def validate_citation_markers(
    narrative: str,
    *,
    max_citation_id: int,
) -> dict:
    """Ensure [n] markers reference valid citation ids (1..max_citation_id)."""
    if not narrative or max_citation_id <= 0:
        return {"valid": True, "invalid_markers": [], "markers_found": []}

    markers = [int(m) for m in _CITATION_MARKER.findall(narrative)]
    invalid = [m for m in markers if m < 1 or m > max_citation_id]
    return {
        "valid": len(invalid) == 0,
        "invalid_markers": invalid,
        "markers_found": markers,
    }


_BLOCK_CONTRADICTIONS = (
    re.compile(r"\b(safe to buy|go ahead and buy|recommend buying|you should buy)\b", re.I),
    re.compile(r"\b(allow(ed)? to (buy|trade|proceed))\b", re.I),
)


def validate_authority_compliance(narrative: str, risk_verdict: str) -> dict:
    """Flag narratives that contradict a BLOCK/CAUTION risk verdict."""
    if not narrative or not risk_verdict:
        return {"compliant": True, "violations": []}

    if risk_verdict not in {"BLOCK", "CAUTION"}:
        return {"compliant": True, "violations": []}

    violations: list[str] = []
    for pattern in _BLOCK_CONTRADICTIONS:
        if pattern.search(narrative):
            violations.append(pattern.pattern)

    if risk_verdict == "BLOCK" and re.search(r"\b(allow|approved)\b", narrative, re.I):
        violations.append("allow_while_blocked")

    return {"compliant": len(violations) == 0, "violations": violations}


def validate_grounded_reply(
    narrative: str,
    *,
    risk_verdict: str,
    citation_count: int,
) -> dict:
    """Combined citation + authority validation for chat responses."""
    citations = validate_citation_markers(narrative, max_citation_id=citation_count)
    authority = validate_authority_compliance(narrative, risk_verdict)
    return {
        "citations": citations,
        "authority": authority,
        "grounded": citations["valid"] and authority["compliant"],
    }
