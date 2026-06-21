"""Retrain direction model from market data and journal snapshots."""

import structlog

import pandas as pd

from app.core.config import settings
from app.db.storage import get_storage
from app.ml.feature_builder import FEATURE_COLS, TARGET_COL, build_training_frame, macro_from_qqq_bars, qqq_trend_to_numeric
from app.ml.model_registry import list_model_history, load_meta, predict_direction_prob, rollback_to_version
from app.ml.snapshot import journal_target_from_trade
from app.ml.training import train_direction_model
from app.ml.volatility_builder import build_volatility_training_frame
from app.ml.volatility_registry import load_vol_meta
from app.ml.volatility_training import train_volatility_model
from app.providers.market.factory import get_market_data_provider
from app.providers.market.mock import MockMarketDataProvider

logger = structlog.get_logger()

BOOTSTRAP_TICKERS = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]
MACRO_TICKERS = ["SPY", "QQQ"]


class MLRetrainService:
    async def status(self) -> dict:
        meta = load_meta()
        vol_meta = load_vol_meta()
        history = list_model_history()
        return {
            "model_exists": meta.get("version", 0) > 0,
            "version": meta.get("version", 0),
            "model_type": meta.get("model_type", "none"),
            "last_trained_at": meta.get("last_trained_at"),
            "source": meta.get("source", "none"),
            "accuracy": meta.get("accuracy"),
            "auc": meta.get("auc"),
            "brier": meta.get("brier"),
            "deploy_gate_passed": meta.get("deploy_gate_passed", False),
            "feature_importance": meta.get("feature_importance", {}),
            "walk_forward_folds": meta.get("walk_forward_folds"),
            "samples": meta.get("samples"),
            "journal_trades_used": meta.get("journal_trades_used", 0),
            "journal_retrain_enabled": settings.ml_journal_retrain_enabled,
            "min_trades_required": settings.ml_retrain_min_trades,
            "history_versions": len(history),
            "volatility": {
                "enabled": settings.ml_volatility_enabled,
                "model_exists": vol_meta.get("version", 0) > 0,
                "version": vol_meta.get("version", 0),
                "model_type": vol_meta.get("model_type", "none"),
                "last_trained_at": vol_meta.get("last_trained_at"),
                "auc": vol_meta.get("auc"),
                "accuracy": vol_meta.get("accuracy"),
                "feature_importance": vol_meta.get("feature_importance", {}),
                "high_threshold": settings.ml_vol_high_threshold,
            },
        }

    async def history(self) -> dict:
        return {"active": load_meta(), "versions": list_model_history()}

    async def rollback(self, version: int) -> dict:
        result = rollback_to_version(version)
        if result.get("status") != "ok":
            return result
        logger.info("ml_model_rollback", version=version)
        return result

    async def retrain(self) -> dict:
        market = await self._market_training_rows()
        journal = await self._journal_training_rows()
        journal_count = len(journal)

        if journal_count >= settings.ml_retrain_min_trades and not journal.empty:
            dataset = pd.concat([market, journal], ignore_index=True)
            source = "market_and_journal"
        else:
            dataset = market
            source = "market_only"
            journal_count = 0

        if dataset.empty or len(dataset) < settings.ml_min_samples:
            return {"status": "skipped", "reason": "insufficient training data", "samples": len(dataset)}

        result = train_direction_model(
            dataset,
            source=source,
            journal_trades_used=journal_count,
        )
        if result.get("status") == "ok":
            logger.info(
                "ml_retrain_complete",
                version=result.get("version"),
                auc=result.get("auc"),
                model_type=result.get("model_type"),
                journal_trades_used=journal_count,
            )
        else:
            logger.info("ml_retrain_skipped", reason=result.get("reason"), new_auc=result.get("new_auc"))
        result["journal_trades_used"] = journal_count
        result["samples"] = len(dataset)
        result["source"] = source

        if settings.ml_volatility_enabled:
            vol_dataset = await self._volatility_training_rows()
            vol_result = train_volatility_model(vol_dataset, source="macro")
            result["volatility"] = vol_result
            if vol_result.get("status") == "ok":
                logger.info(
                    "ml_vol_retrain_complete",
                    version=vol_result.get("version"),
                    auc=vol_result.get("auc"),
                )

        return result

    async def _journal_training_rows(self) -> pd.DataFrame:
        if not settings.ml_journal_retrain_enabled:
            return pd.DataFrame()

        storage = await get_storage()
        trades = await storage.list_paper_trades(limit=500)
        rows: list[dict] = []

        for trade in trades:
            if trade.get("status") != "filled":
                continue
            pnl = trade.get("pnl")
            if pnl is None:
                continue
            approval_id = trade.get("approval_id")
            if not approval_id:
                continue

            approval = await storage.get_approval_request(approval_id)
            if not approval:
                continue

            snapshot = (approval.get("risk_preview") or {}).get("ml_snapshot")
            if not snapshot:
                continue

            try:
                row = {col: float(snapshot[col]) for col in FEATURE_COLS}
            except (KeyError, TypeError, ValueError):
                continue

            side = str(trade.get("side", "buy"))
            row[TARGET_COL] = journal_target_from_trade(side, float(pnl))
            row["ticker"] = trade.get("ticker", "")
            rows.append(row)

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    async def _market_training_rows(self) -> pd.DataFrame:
        provider = get_market_data_provider()
        mock = MockMarketDataProvider()
        qqq_bars = await provider.get_macro_bars("QQQ", days=60)
        if len(qqq_bars) < 20:
            qqq_bars = await mock.get_macro_bars("QQQ", days=60)
        qqq_trend, vix_change = macro_from_qqq_bars(qqq_bars)
        qqq_num = qqq_trend_to_numeric(qqq_trend)

        rows = []
        for ticker in BOOTSTRAP_TICKERS:
            bars = await provider.get_daily_bars(ticker, days=180)
            if len(bars) < 60:
                bars = await mock.get_daily_bars(ticker, days=180)
            frame = build_training_frame(
                bars,
                ticker=ticker,
                news_sentiment=50.0,
                qqq_trend_numeric=qqq_num,
                vix_change=vix_change,
                regime_risk_adj=0.0,
            )
            if not frame.empty:
                rows.append(frame)
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    async def _volatility_training_rows(self) -> pd.DataFrame:
        provider = get_market_data_provider()
        mock = MockMarketDataProvider()
        qqq_bars = await provider.get_macro_bars("QQQ", days=60)
        if len(qqq_bars) < 20:
            qqq_bars = await mock.get_macro_bars("QQQ", days=60)
        qqq_trend, vix_change = macro_from_qqq_bars(qqq_bars)
        qqq_num = qqq_trend_to_numeric(qqq_trend)

        rows = []
        for ticker in MACRO_TICKERS:
            bars = await provider.get_macro_bars(ticker, days=180)
            if len(bars) < 60:
                bars = await mock.get_macro_bars(ticker, days=180)
            frame = build_volatility_training_frame(
                bars,
                ticker=ticker,
                qqq_trend_numeric=qqq_num,
                vix_change=vix_change,
            )
            if not frame.empty:
                rows.append(frame)
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    @staticmethod
    def sample_prediction() -> float:
        import numpy as np

        sample = np.array([2.0, 1.0, 55.0, 0.1, 2.5, 1.1, 50.0, 1.0, 2.0, 0.0])
        return predict_direction_prob(sample)
