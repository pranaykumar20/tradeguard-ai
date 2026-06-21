"""Index ML retrain run summaries for model lineage RAG retrieval."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.rag.pipeline import RAGIngestPipeline

logger = structlog.get_logger()


def build_ml_run_document(result: dict) -> dict | None:
    if result.get("status") != "ok":
        return None

    version = result.get("version", 0)
    as_of = datetime.now(timezone.utc).isoformat()
    date_key = as_of[:10]
    auc = result.get("auc")
    model_type = result.get("model_type", "unknown")
    source = result.get("source", "market_only")
    journal_used = result.get("journal_trades_used", 0)
    samples = result.get("samples", 0)
    importance = result.get("feature_importance") or {}
    top_features = ", ".join(list(importance.keys())[:5]) if importance else "n/a"

    auc_part = f" walk-forward AUC {auc:.3f}." if isinstance(auc, (int, float)) else ""
    content = (
        f"Direction model v{version} ({model_type}) deployed {date_key}.{auc_part} "
        f"Training source {source} with {samples} samples; "
        f"journal-augmented trades {journal_used}. "
        f"Top features: {top_features}."
    )

    return {
        "chunk_id": f"ml-run-v{version}-{date_key}",
        "source": f"ML retrain — direction v{version}",
        "content": content,
        "meta": {
            "type": "ml_run",
            "model_version": version,
            "model_type": model_type,
            "trained_at": as_of,
            "auc": auc,
            "source": source,
            "journal_trades_used": journal_used,
            "visibility": "global",
        },
    }


async def index_ml_run(result: dict) -> int:
    doc = build_ml_run_document(result)
    if not doc:
        return 0
    ingest_result = await RAGIngestPipeline().ingest([doc], skip_chunking=True)
    logger.info("rag_ml_run_indexed", version=result.get("version"), stored=ingest_result["stored"])
    return int(ingest_result["stored"])
