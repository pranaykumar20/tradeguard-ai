"""Playbook section chunking — split long sections for better retrieval."""

from __future__ import annotations

from app.rag.chunking import chunk_text

MAX_PLAYBOOK_CHARS = 800
PLAYBOOK_OVERLAP = 80


def chunk_playbook_documents(documents: list[dict]) -> list[dict]:
    chunked: list[dict] = []
    for doc in documents:
        content = doc.get("content", "")
        if len(content) <= MAX_PLAYBOOK_CHARS:
            chunked.append(doc)
            continue

        base_id = doc.get("chunk_id") or doc.get("id", "playbook")
        meta = dict(doc.get("meta") or {})
        parent_id = base_id
        meta["parent_id"] = parent_id

        for index, piece in enumerate(
            chunk_text(content, max_chars=MAX_PLAYBOOK_CHARS, overlap=PLAYBOOK_OVERLAP),
            start=1,
        ):
            piece_meta = {**meta, "chunk_index": index, "parent_id": parent_id}
            chunked.append(
                {
                    **doc,
                    "chunk_id": f"{base_id}-part-{index:02d}",
                    "content": piece,
                    "meta": piece_meta,
                }
            )
    return chunked
