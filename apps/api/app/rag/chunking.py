"""Text chunking utilities for RAG ingestion."""

from __future__ import annotations

import re


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&#\d+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            split_at = cleaned.rfind(". ", start, end)
            if split_at > start + max_chars // 2:
                end = split_at + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
    match = re.search(start_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    remainder = text[match.end() :]
    end = re.search(end_pattern, remainder, flags=re.IGNORECASE | re.DOTALL)
    body = remainder[: end.start()] if end else remainder[:8000]
    return re.sub(r"\s+", " ", body).strip()
