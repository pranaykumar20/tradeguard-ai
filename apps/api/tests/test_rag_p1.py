"""Phase 5 P1 — operational corpora, temporal filters, new RAG tools."""

from datetime import datetime, timedelta, timezone

from app.rag.indexers.analysis_snapshot import build_analysis_snapshot_document
from app.rag.indexers.ml_run import build_ml_run_document
from app.rag.retrieval import apply_temporal_filter, parse_temporal_window
from app.rag.tools import infer_rag_tools


def test_build_analysis_snapshot_document():
    doc = build_analysis_snapshot_document(
        {
            "ticker": "NVDA",
            "composite_score": 72.0,
            "composite_score_adjusted": 68.0,
            "setup_label": "Strong",
            "risk_verdict": "CAUTION",
            "warnings": ["High concentration"],
            "regime": {"label": "risk_off"},
            "features": {"ml_bullish_prob": 0.55},
        }
    )
    assert doc["meta"]["type"] == "analysis_snapshot"
    assert "NVDA" in doc["content"]
    assert doc["meta"]["risk_verdict"] == "CAUTION"


def test_build_ml_run_document():
    doc = build_ml_run_document(
        {
            "status": "ok",
            "version": 3,
            "auc": 0.61,
            "model_type": "xgboost",
            "source": "market_and_journal",
            "journal_trades_used": 12,
            "samples": 400,
            "feature_importance": {"rsi_14": 0.2, "price_vs_50dma": 0.15},
        }
    )
    assert doc is not None
    assert doc["meta"]["type"] == "ml_run"
    assert "v3" in doc["content"]


def test_parse_temporal_window_last_month():
    window = parse_temporal_window("what did we think about NVDA last month")
    assert window is not None
    start, end = window
    assert (end - start).days >= 29


def test_apply_temporal_filter():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=3)).isoformat()
    old = (now - timedelta(days=60)).isoformat()
    docs = [
        {"chunk_id": "a", "meta": {"type": "analysis_snapshot", "as_of": recent}},
        {"chunk_id": "b", "meta": {"type": "analysis_snapshot", "as_of": old}},
    ]
    filtered = apply_temporal_filter(docs, "NVDA analysis last week")
    assert len(filtered) == 1
    assert filtered[0]["chunk_id"] == "a"


def test_infer_rag_tools_analysis_and_ml():
    tools = infer_rag_tools("what did we think about NVDA last month?")
    assert "search_analysis_history" in tools

    tools = infer_rag_tools("what is the model auc after retrain?")
    assert "search_ml_runs" in tools
