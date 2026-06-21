"""Type-specific document chunkers for RAG ingestion."""

from __future__ import annotations

from app.rag.chunkers.filing import chunk_filing_documents
from app.rag.chunkers.news import chunk_news_documents
from app.rag.chunkers.playbook import chunk_playbook_documents

_CHUNKERS = {
    "playbook": chunk_playbook_documents,
    "filing": chunk_filing_documents,
    "news": chunk_news_documents,
}


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Apply type-specific chunking; pass through unknown types unchanged."""
    result: list[dict] = []
    for doc in documents:
        doc_type = (doc.get("meta") or {}).get("type", "document")
        chunker = _CHUNKERS.get(doc_type)
        if chunker:
            result.extend(chunker([doc]))
        else:
            result.append(doc)
    return result
