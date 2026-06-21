"""ML pipeline tests — feature parity, training, registry, hybrid risk."""

import numpy as np
import pandas as pd
import pytest

from app.ml.feature_builder import FEATURE_COLS, build_training_frame, feature_vector_from_dict, latest_feature_row
from app.ml.model_registry import MODEL_PATH, load_meta, predict_direction, reload_model, save_meta
from app.ml.training import train_direction_model, walk_forward_metrics
from app.providers.market.mock import MockMarketDataProvider
from app.risk.engine import RiskEngine


@pytest.fixture
def sample_bars():
    provider = MockMarketDataProvider()
    import asyncio

    return asyncio.run(provider.get_daily_bars("NVDA", days=180))


def test_feature_builder_training_and_inference_match(sample_bars):
    frame = build_training_frame(
        sample_bars,
        ticker="NVDA",
        news_sentiment=55.0,
        qqq_trend_numeric=1.0,
        vix_change=2.5,
        regime_risk_adj=-2.0,
    )
    assert not frame.empty
    assert set(FEATURE_COLS).issubset(frame.columns)

    latest = latest_feature_row(
        sample_bars,
        news_sentiment=55.0,
        qqq_trend="bullish",
        vix_change=2.5,
        regime_risk_adj=-2.0,
    )
    last_row = frame.iloc[-1]
    for col in FEATURE_COLS:
        if col in {"news_sentiment_score", "qqq_trend_numeric", "vix_change", "regime_risk_adj"}:
            assert float(latest[col]) == float(last_row[col])
        else:
            assert abs(float(latest[col]) - float(last_row[col])) < 0.15


def test_walk_forward_metrics_returns_auc(sample_bars):
    frame = build_training_frame(sample_bars, news_sentiment=50.0, qqq_trend_numeric=0.5, vix_change=2.0)
    metrics = walk_forward_metrics(frame)
    assert "auc" in metrics
    assert "accuracy" in metrics
    assert metrics["samples"] == len(frame)


def test_train_and_registry_cache(tmp_path, monkeypatch, sample_bars):
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr("app.ml.model_registry.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.model_registry.MODEL_PATH", artifacts / "direction_model.joblib")
    monkeypatch.setattr("app.ml.model_registry.META_PATH", artifacts / "model_meta.json")
    monkeypatch.setattr("app.ml.training.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.training.MODEL_PATH", artifacts / "direction_model.joblib")

    frame = build_training_frame(sample_bars, news_sentiment=50.0, qqq_trend_numeric=1.0, vix_change=2.0)
    result = train_direction_model(frame, force_deploy=True)
    assert result["status"] == "ok"
    assert MODEL_PATH.exists()

    reload_model()
    vector = feature_vector_from_dict(latest_feature_row(sample_bars, qqq_trend="bullish", vix_change=2.0))
    out1 = predict_direction(vector)
    out2 = predict_direction(vector)
    assert 0 <= out1["prob"] <= 1
    assert out1["prob"] == out2["prob"]
    assert "confidence" in out1
    assert "direction" in out1


def test_deploy_gate_blocks_worse_model(tmp_path, monkeypatch, sample_bars):
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr("app.ml.model_registry.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.model_registry.MODEL_PATH", artifacts / "direction_model.joblib")
    monkeypatch.setattr("app.ml.model_registry.META_PATH", artifacts / "model_meta.json")
    monkeypatch.setattr("app.ml.training.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.training.MODEL_PATH", artifacts / "direction_model.joblib")

    save_meta({"version": 1, "auc": 0.99, "accuracy": 0.99})
    frame = build_training_frame(sample_bars, news_sentiment=50.0, qqq_trend_numeric=1.0, vix_change=2.0)
    result = train_direction_model(frame, force_deploy=False)
    assert result["status"] == "skipped"
    assert result["reason"] == "deploy_gate_failed"


@pytest.mark.asyncio
async def test_hybrid_ml_caution_on_low_bullish_buy():
    engine = RiskEngine()
    features = {
        "ml_bullish_prob": 0.35,
        "ml_confidence": 0.2,
        "ml_model_version": 3,
        "rsi_14": 50,
        "vix_change": 2,
        "qqq_trend": "bullish",
        "atr_percent": 2,
    }
    scores = {"composite": 60, "components": {"risk": 60}, "ml_confidence": 0.2}
    verdict = engine.evaluate_ticker("NVDA", features, scores, side="buy")
    assert verdict.verdict == "CAUTION"
    assert any("ML model is not bullish" in w for w in verdict.warnings)


def test_build_ml_snapshot():
    from app.ml.snapshot import build_ml_snapshot, journal_target_from_trade

    features = {col: float(i + 1) for i, col in enumerate(FEATURE_COLS)}
    features.update({"ml_bullish_prob": 0.62, "ml_confidence": 0.24, "ml_model_version": 2})
    snap = build_ml_snapshot(features, {"composite": 71.5})
    assert set(FEATURE_COLS).issubset(snap.keys())
    assert snap["ml_model_version"] == 2
    assert snap["composite_score"] == 71.5

    assert journal_target_from_trade("buy", 100.0) == 1
    assert journal_target_from_trade("buy", -50.0) == 0
    assert journal_target_from_trade("sell", 100.0) == 0
    assert journal_target_from_trade("sell", -50.0) == 1


def test_model_archive_and_rollback(tmp_path, monkeypatch, sample_bars):
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr("app.ml.model_registry.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.model_registry.MODEL_PATH", artifacts / "direction_model.joblib")
    monkeypatch.setattr("app.ml.model_registry.META_PATH", artifacts / "model_meta.json")
    monkeypatch.setattr("app.ml.model_registry.HISTORY_PATH", artifacts / "model_history.json")
    monkeypatch.setattr("app.ml.training.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.training.MODEL_PATH", artifacts / "direction_model.joblib")

    frame = build_training_frame(sample_bars, news_sentiment=50.0, qqq_trend_numeric=1.0, vix_change=2.0)
    first = train_direction_model(frame, force_deploy=True)
    assert first["status"] == "ok"
    v1 = first["version"]

    second = train_direction_model(frame, force_deploy=True)
    assert second["status"] == "ok"
    assert second["version"] == v1 + 1

    history = __import__("app.ml.model_registry", fromlist=["list_model_history"]).list_model_history()
    assert any(entry["version"] == v1 for entry in history)

    rollback = __import__("app.ml.model_registry", fromlist=["rollback_to_version"]).rollback_to_version(v1)
    assert rollback["status"] == "ok"
    assert load_meta()["version"] == v1


@pytest.mark.asyncio
async def test_journal_training_rows_from_snapshots(monkeypatch):
    from app.ml.snapshot import build_ml_snapshot
    from app.services.ml_retrain import MLRetrainService

    features = {col: 1.0 for col in FEATURE_COLS}
    features.update({"ml_bullish_prob": 0.55, "ml_confidence": 0.1, "ml_model_version": 1})
    snapshot = build_ml_snapshot(features)

    class FakeStorage:
        async def list_paper_trades(self, limit=100):
            return [
                {
                    "status": "filled",
                    "pnl": 120.0,
                    "approval_id": "apr-1",
                    "side": "buy",
                    "ticker": "NVDA",
                }
            ]

        async def get_approval_request(self, request_id):
            return {"risk_preview": {"ml_snapshot": snapshot}}

    async def fake_get_storage():
        return FakeStorage()

    monkeypatch.setattr("app.services.ml_retrain.get_storage", fake_get_storage)
    monkeypatch.setattr("app.services.ml_retrain.settings.ml_journal_retrain_enabled", True)

    rows = await MLRetrainService()._journal_training_rows()
    assert len(rows) == 1
    assert int(rows.iloc[0]["target_up_5d"]) == 1


@pytest.fixture
def macro_bars():
    provider = MockMarketDataProvider()
    import asyncio

    return asyncio.run(provider.get_macro_bars("SPY", days=180))


def test_volatility_builder_training_frame(macro_bars):
    from app.ml.volatility_builder import TARGET_VOL_COL, VOL_FEATURE_COLS, build_volatility_training_frame

    frame = build_volatility_training_frame(
        macro_bars,
        ticker="SPY",
        qqq_trend_numeric=1.0,
        vix_change=2.5,
    )
    assert not frame.empty
    assert set(VOL_FEATURE_COLS).issubset(frame.columns)
    assert TARGET_VOL_COL in frame.columns
    assert frame[TARGET_VOL_COL].isin([0, 1]).all()


def test_train_volatility_model(tmp_path, monkeypatch, macro_bars):
    from app.ml.volatility_builder import build_volatility_training_frame
    from app.ml.volatility_registry import VOL_META_PATH, VOL_MODEL_PATH, load_vol_meta
    from app.ml.volatility_training import train_volatility_model

    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr("app.ml.volatility_registry.ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr("app.ml.volatility_registry.VOL_MODEL_PATH", artifacts / "volatility_model.joblib")
    monkeypatch.setattr("app.ml.volatility_registry.VOL_META_PATH", artifacts / "volatility_meta.json")

    frame = build_volatility_training_frame(macro_bars, qqq_trend_numeric=1.0, vix_change=2.0)
    result = train_volatility_model(frame, force_deploy=True)
    assert result["status"] == "ok"
    assert VOL_MODEL_PATH.exists()
    assert load_vol_meta()["version"] >= 1


@pytest.mark.asyncio
async def test_regime_blends_ml_volatility(monkeypatch):
    from app.services.regime import RegimeService

    async def fake_detect_features(ticker, use_cache=True):
        return {
            "vix_change": 2.0,
            "qqq_trend": "bullish",
            "rsi_14": 58,
            "atr_percent": 2.0,
        }

    async def fake_ml_vol(self):
        return {"prob": 0.72, "confidence": 0.44, "regime_hint": "high_vol", "version": 2}

    monkeypatch.setattr("app.services.regime.compute_ticker_features", fake_detect_features)
    monkeypatch.setattr(RegimeService, "_ml_vol_prediction", fake_ml_vol)
    monkeypatch.setattr("app.services.regime.settings.ml_volatility_enabled", True)
    monkeypatch.setattr("app.services.regime.settings.ml_vol_high_threshold", 0.55)

    data = await RegimeService().detect()
    assert data["regime"] == "high_vol"
    assert data["ml_vol_prob"] == 0.72
