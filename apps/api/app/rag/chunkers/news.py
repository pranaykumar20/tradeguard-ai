"""News chunking — title + summary for richer retrieval."""

from __future__ import annotations


def chunk_news_documents(documents: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for doc in documents:
        meta = dict(doc.get("meta") or {})
        title = meta.get("title") or _extract_title(doc.get("content", ""))
        summary = (meta.get("summary") or "").strip()
        source = meta.get("source_name") or meta.get("source") or ""

        parts = [title]
        if summary and summary.lower() not in title.lower():
            parts.append(summary)
        if source and source not in title:
            parts.append(f"Source: {source}")

        content = ". ".join(p for p in parts if p)
        meta.setdefault("title", title)
        meta.setdefault("visibility", "global")
        enriched.append({**doc, "content": content, "meta": meta})
    return enriched


def _extract_title(content: str) -> str:
    if "(source:" in content.lower():
        return content.split("(source:")[0].strip()
    return content.strip()
