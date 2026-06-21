"""Filing chunk enrichment — parent-child metadata for multi-part sections."""

from __future__ import annotations

import re


def chunk_filing_documents(documents: list[dict]) -> list[dict]:
    """Enrich filing chunks with parent_id for context expansion."""
    grouped: dict[str, list[dict]] = {}
    for doc in documents:
        chunk_id = doc.get("chunk_id") or ""
        parent = _filing_parent_id(chunk_id)
        grouped.setdefault(parent, []).append(doc)

    enriched: list[dict] = []
    for parent_id, group in grouped.items():
        for doc in group:
            meta = dict(doc.get("meta") or {})
            meta.setdefault("parent_id", parent_id)
            if "-part-" not in (doc.get("chunk_id") or ""):
                match = re.search(r"-(\d{2})$", doc.get("chunk_id") or "")
                if match:
                    meta["chunk_index"] = int(match.group(1))
            enriched.append({**doc, "meta": meta})
    return enriched


def _filing_parent_id(chunk_id: str) -> str:
    if "-part-" in chunk_id:
        return chunk_id.rsplit("-part-", 1)[0]
    match = re.match(r"^(sec-[a-z0-9]+-10k-[a-z-]+)", chunk_id)
    if match:
        return match.group(1)
    return chunk_id
