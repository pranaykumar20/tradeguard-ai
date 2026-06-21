"""Re-embed RAG chunks when embedding_version changes."""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.providers.embeddings.factory import embed_documents_by_type
from app.rag.pipeline import content_hash, normalize_document

logger = structlog.get_logger()


async def reembed_stale_chunks(*, batch_size: int = 50) -> dict:
    if not settings.rag_embedding_migration_enabled:
        return {"status": "disabled", "reembedded": 0}

    storage = await get_storage()
    all_docs = await storage.list_rag_documents_raw()
    target_version = settings.rag_embedding_version

    stale = [
        doc
        for doc in all_docs
        if int((doc.get("meta") or {}).get("embedding_version", 0)) < target_version
    ]
    if not stale:
        return {"status": "ok", "reembedded": 0, "skipped": len(all_docs)}

    reembedded = 0
    for start in range(0, len(stale), batch_size):
        batch = stale[start : start + batch_size]
        normalized = []
        for doc in batch:
            normalized_doc = normalize_document(
                {
                    "chunk_id": doc["chunk_id"],
                    "source": doc["source"],
                    "content": doc["content"],
                    "meta": doc.get("meta") or {},
                }
            )
            normalized_doc["meta"]["embedding_version"] = target_version
            normalized_doc["meta"]["content_hash"] = content_hash(normalized_doc["content"])
            normalized.append(normalized_doc)

        embedded = await embed_documents_by_type(normalized)
        await storage.upsert_rag_documents(
            [
                {
                    "chunk_id": d["chunk_id"],
                    "source": d["source"],
                    "content": d["content"],
                    "embedding": d["embedding"],
                    "meta": d["meta"],
                }
                for d in embedded
            ]
        )
        reembedded += len(embedded)

    logger.info("rag_embedding_migration_complete", reembedded=reembedded, total_stale=len(stale))
    return {"status": "ok", "reembedded": reembedded, "total_stale": len(stale)}
