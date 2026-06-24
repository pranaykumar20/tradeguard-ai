"""Index macro regime snapshots for RAG retrieval."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.rag.pipeline import RAGIngestPipeline
from app.services.regime import RegimeService

logger = structlog.get_logger()


def build_regime_snapshot_document(regime: dict) -> dict:
    as_of = datetime.now(timezone.utc).isoformat()
    date_key = as_of[:10]
    label = regime.get("label", "Unknown")
    regime_key = regime.get("regime", "neutral")
    adjustment = regime.get("risk_score_adjustment", 0)
    signals = regime.get("signals") or {}
    ml_prob = regime.get("ml_vol_prob")
    ml_conf = regime.get("ml_vol_confidence")

    signal_bits = ", ".join(f"{k}={v}" for k, v in list(signals.items())[:6]) or "none"
    ml_part = ""
    if isinstance(ml_prob, (int, float)):
        ml_part = f" ML vol prob {ml_prob:.2f} (confidence {float(ml_conf or 0):.2f})."

    content = (
        f"Market regime as of {date_key}: {label} ({regime_key}). "
        f"Risk score adjustment {adjustment:+d}.{ml_part} "
        f"Signals: {signal_bits}."
    )

    return {
        "chunk_id": f"regime-{date_key}",
        "source": "Macro regime snapshot",
        "content": content,
        "meta": {
            "type": "regime_snapshot",
            "as_of": as_of,
            "regime": regime_key,
            "label": label,
            "risk_score_adjustment": adjustment,
            "ml_vol_prob": ml_prob,
            "ml_vol_confidence": ml_conf,
            "visibility": "global",
            "staleness_class": "daily",
        },
    }


async def index_regime_snapshot() -> int:
    regime = await RegimeService().detect()
    doc = build_regime_snapshot_document(regime)
    result = await RAGIngestPipeline().ingest([doc], skip_chunking=True)
    logger.info("rag_regime_snapshot_indexed", stored=result["stored"], regime=regime.get("regime"))
    return int(result["stored"])
