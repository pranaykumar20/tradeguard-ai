"""Retrain direction model from journal outcomes — Phase 6.2."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.ml.training import ARTIFACTS_DIR, FEATURE_COLS, predict_direction, train_direction_model
from app.providers.market.factory import get_market_data_provider
from app.providers.market.mock import MockMarketDataProvider

logger = structlog.get_logger()
META_PATH = ARTIFACTS_DIR / "model_meta.json"
BOOTSTRAP_TICKERS = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]


class MLRetrainService:
    async def status(self) -> dict:
        meta = self._load_meta()
        path = ARTIFACTS_DIR / "direction_model.joblib"
        return {
            "model_exists": path.exists(),
            "version": meta.get("version", 1),
            "last_trained_at": meta.get("last_trained_at"),
            "source": meta.get("source", "bootstrap"),
            "accuracy": meta.get("accuracy"),
            "journal_trades_used": meta.get("journal_trades_used", 0),
            "min_trades_required": settings.ml_retrain_min_trades,
        }

    async def retrain(self) -> dict:
        storage = await get_storage()
        trades = await storage.list_paper_trades(limit=500)
        filled = [t for t in trades if t.get("status") == "filled" and t.get("pnl") is not None]

        market_rows = await self._market_training_rows()
        journal_rows = await self._journal_training_rows(filled)

        if len(journal_rows) >= settings.ml_retrain_min_trades:
            dataset = pd.concat([market_rows, journal_rows], ignore_index=True)
            source = "journal+market"
        else:
            dataset = market_rows
            source = "market_only"

        if dataset.empty or len(dataset) < 30:
            return {"status": "skipped", "reason": "insufficient training data"}

        metrics = train_direction_model(dataset, feature_cols=FEATURE_COLS)
        meta = self._load_meta()
        version = int(meta.get("version", 1)) + 1
        self._save_meta(
            {
                "version": version,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "accuracy": metrics.get("accuracy"),
                "journal_trades_used": len(journal_rows),
            }
        )
        logger.info("ml_retrain_complete", version=version, source=source, accuracy=metrics.get("accuracy"))
        return {
            "status": "ok",
            "version": version,
            "source": source,
            "accuracy": metrics.get("accuracy"),
            "journal_trades_used": len(journal_rows),
            "samples": len(dataset),
        }

    async def _market_training_rows(self) -> pd.DataFrame:
        provider = get_market_data_provider()
        mock = MockMarketDataProvider()
        rows = []
        for ticker in BOOTSTRAP_TICKERS:
            bars = await provider.get_daily_bars(ticker, days=180)
            if len(bars) < 60:
                bars = await mock.get_daily_bars(ticker, days=180)
            close = bars["close"]
            ret5 = close.pct_change(5).shift(-5)
            df = pd.DataFrame(
                {
                    "price_vs_20dma": (close - close.rolling(20).mean()) / close.rolling(20).mean() * 100,
                    "price_vs_50dma": (close - close.rolling(50).mean()) / close.rolling(50).mean() * 100,
                    "rsi_14": close.pct_change().rolling(14).std() * 100,
                    "macd_signal": close.diff().rolling(5).mean(),
                    "atr_percent": (close.rolling(14).max() - close.rolling(14).min()) / close * 100,
                    "volume_spike": bars["volume"] / bars["volume"].rolling(20).mean(),
                    "target_up_5d": (ret5 > 0).astype(int),
                }
            ).dropna()
            rows.append(df)
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    async def _journal_training_rows(self, filled: list[dict]) -> pd.DataFrame:
        rows = []
        for trade in filled:
            ticker = trade.get("ticker", "QQQ")
            try:
                from app.services.features import compute_ticker_features

                features = await compute_ticker_features(ticker, use_cache=True)
            except Exception:
                continue
            try:
                vector = np.array(
                    [
                        float(features["price_vs_20dma"]),
                        float(features["price_vs_50dma"]),
                        float(features["rsi_14"]),
                        float(features["macd_signal"]),
                        float(features["atr_percent"]),
                        float(features["volume_spike"]),
                    ]
                )
            except (KeyError, TypeError, ValueError):
                continue
            target = 1 if (trade.get("pnl") or 0) > 0 else 0
            rows.append(
                {
                    "price_vs_20dma": vector[0],
                    "price_vs_50dma": vector[1],
                    "rsi_14": vector[2],
                    "macd_signal": vector[3],
                    "atr_percent": vector[4],
                    "volume_spike": vector[5],
                    "target_up_5d": target,
                }
            )
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def _load_meta() -> dict:
        if META_PATH.exists():
            return json.loads(META_PATH.read_text())
        return {}

    @staticmethod
    def _save_meta(meta: dict) -> None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        META_PATH.write_text(json.dumps(meta, indent=2))

    @staticmethod
    def sample_prediction() -> float:
        sample = np.array([2.0, 1.0, 55.0, 0.1, 2.5, 1.1])
        return predict_direction(sample)
