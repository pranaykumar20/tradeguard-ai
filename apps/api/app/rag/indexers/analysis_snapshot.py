"""Index ticker analysis snapshots for historical RAG retrieval."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.rag.pipeline import RAGIngestPipeline

logger = structlog.get_logger()


def build_analysis_snapshot_document(analysis: dict) -> dict:
    ticker = str(analysis.get("ticker", "")).upper()
    as_of = datetime.now(timezone.utc).isoformat()
    date_key = as_of[:10]

    composite = analysis.get("composite_score_adjusted") or analysis.get("composite_score", 0)
    verdict = analysis.get("risk_verdict", "UNKNOWN")
    label = analysis.get("setup_label", "")
    regime = (analysis.get("regime") or {}).get("label", "unknown")
    features = analysis.get("features") or {}
    ml_prob = features.get("ml_bullish_prob", features.get("ml_prob"))

    ml_part = f" ML bullish prob {ml_prob:.2f}." if isinstance(ml_prob, (int, float)) else ""
    content = (
        f"{ticker} analysis as of {date_key}: composite score {composite:.1f}, "
        f"setup {label}, regime {regime}, verdict {verdict}.{ml_part} "
        f"Warnings: {', '.join(analysis.get('warnings') or []) or 'none'}."
    )

    return {
        "chunk_id": f"analysis-{ticker.lower()}-{date_key}",
        "source": f"Analysis snapshot — {ticker}",
        "content": content,
        "meta": {
            "type": "analysis_snapshot",
            "ticker": ticker,
            "as_of": as_of,
            "composite_score": composite,
            "setup_label": label,
            "risk_verdict": verdict,
            "regime": regime,
            "visibility": "global",
        },
    }


async def index_analysis_snapshot(analysis: dict) -> int:
    doc = build_analysis_snapshot_document(analysis)
    result = await RAGIngestPipeline().ingest([doc], skip_chunking=True)
    logger.info(
        "rag_analysis_snapshot_indexed",
        ticker=analysis.get("ticker"),
        stored=result["stored"],
    )
    return int(result["stored"])
