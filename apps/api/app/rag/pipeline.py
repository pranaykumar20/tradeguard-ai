"""Unified RAG ingestion — normalize, chunk, dedupe, embed, upsert."""

from __future__ import annotations

import hashlib

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.providers.embeddings.factory import embed_documents_by_type
from app.rag.chunkers import chunk_documents
from app.rag.service import RAGService

logger = structlog.get_logger()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_document(doc: dict) -> dict:
    meta = dict(doc.get("meta") or {})
    doc_type = meta.get("type", "document")
    meta.setdefault("type", doc_type)
    meta.setdefault("visibility", "global")
    meta.setdefault("embedding_version", settings.rag_embedding_version)
    return {
        "chunk_id": doc.get("chunk_id") or doc.get("id"),
        "source": doc.get("source", "upload"),
        "content": (doc.get("content") or "").strip(),
        "meta": meta,
    }


class RAGIngestPipeline:
    def __init__(self, rag: RAGService | None = None):
        self.rag = rag or RAGService()

    async def filter_unchanged(self, documents: list[dict]) -> tuple[list[dict], int]:
        if not settings.rag_content_hash_enabled or not documents:
            return documents, 0

        storage = await get_storage()
        chunk_ids = [d["chunk_id"] for d in documents if d.get("chunk_id")]
        existing = await storage.get_rag_content_hashes(chunk_ids)

        to_embed: list[dict] = []
        skipped = 0
        for doc in documents:
            digest = content_hash(doc["content"])
            doc["meta"]["content_hash"] = digest
            if existing.get(doc["chunk_id"]) == digest:
                skipped += 1
                continue
            to_embed.append(doc)
        return to_embed, skipped

    async def ingest(
        self,
        documents: list[dict],
        *,
        skip_chunking: bool = False,
    ) -> dict:
        if not documents:
            return {"stored": 0, "skipped": 0, "chunks": 0}

        normalized = [normalize_document(doc) for doc in documents if doc.get("content")]
        normalized = [doc for doc in normalized if doc["chunk_id"]]
        if not skip_chunking:
            normalized = chunk_documents(normalized)

        to_embed, skipped = await self.filter_unchanged(normalized)
        if not to_embed:
            logger.info("rag_ingest_all_unchanged", skipped=skipped, total=len(normalized))
            return {"stored": 0, "skipped": skipped, "chunks": len(normalized)}

        embedded = await embed_documents_by_type(to_embed)
        stored = await self.rag.store_documents(embedded)
        self.rag.mark_ready()
        result = {"stored": stored, "skipped": skipped, "chunks": len(normalized)}
        logger.info("rag_ingest_complete", **result)
        return result
