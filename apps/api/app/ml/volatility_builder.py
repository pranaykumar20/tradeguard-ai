"""Macro volatility features — shared train/inference for regime classifier."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.feature_builder import _compute_series, macro_from_qqq_bars, qqq_trend_to_numeric

VOL_FEATURE_COLS = [
    "atr_percent",
    "rsi_14",
    "volume_spike",
    "price_vs_20dma",
    "price_vs_50dma",
    "realized_vol_10d",
    "vix_change",
    "qqq_trend_numeric",
]

TARGET_VOL_COL = "target_high_vol_5d"
HIGH_VOL_FORWARD_STD_PCT = 2.0


def _realized_vol_series(close: pd.Series, window: int = 10) -> pd.Series:
    returns = close.pct_change()
    return returns.rolling(window).std() * 100


def _forward_vol_target(close: pd.Series, horizon: int = 5) -> pd.Series:
    """1 if forward realized vol is in the top quartile of the sample."""
    returns = close.pct_change()
    forward_std = returns.rolling(horizon).std().shift(-horizon) * 100
    threshold = forward_std.quantile(0.75)
    if pd.isna(threshold) or threshold <= 0:
        threshold = HIGH_VOL_FORWARD_STD_PCT
    return (forward_std >= threshold).astype(int)


def build_volatility_training_frame(
    bars: pd.DataFrame,
    *,
    ticker: str = "",
    qqq_trend_numeric: float = 0.5,
    vix_change: float = 2.0,
) -> pd.DataFrame:
    if len(bars) < 60:
        return pd.DataFrame()

    close = bars["close"]
    features = _compute_series(bars)
    features["realized_vol_10d"] = _realized_vol_series(close)
    features["vix_change"] = float(vix_change)
    features["qqq_trend_numeric"] = float(qqq_trend_numeric)
    features[TARGET_VOL_COL] = _forward_vol_target(close)

    keep = VOL_FEATURE_COLS + [TARGET_VOL_COL]
    if ticker:
        features["ticker"] = ticker
        keep.append("ticker")
    return features[keep].dropna()


def latest_volatility_features(
    bars: pd.DataFrame,
    *,
    qqq_trend: str = "bullish",
    vix_change: float = 2.0,
) -> dict[str, float]:
    if bars.empty:
        raise ValueError("bars must not be empty")

    features = _compute_series(bars)
    close = bars["close"]
    last = features.iloc[-1]
    realized = _realized_vol_series(close).iloc[-1]

    return {
        "atr_percent": round(float(last["atr_percent"]), 2) if pd.notna(last["atr_percent"]) else 0.0,
        "rsi_14": round(float(last["rsi_14"]), 1) if pd.notna(last["rsi_14"]) else 50.0,
        "volume_spike": round(float(last["volume_spike"]), 2) if pd.notna(last["volume_spike"]) else 1.0,
        "price_vs_20dma": round(float(last["price_vs_20dma"]), 2) if pd.notna(last["price_vs_20dma"]) else 0.0,
        "price_vs_50dma": round(float(last["price_vs_50dma"]), 2) if pd.notna(last["price_vs_50dma"]) else 0.0,
        "realized_vol_10d": round(float(realized), 2) if pd.notna(realized) else 0.0,
        "vix_change": round(float(vix_change), 1),
        "qqq_trend_numeric": qqq_trend_to_numeric(qqq_trend),
    }


def volatility_vector_from_dict(features: dict) -> np.ndarray:
    return np.array([float(features[col]) for col in VOL_FEATURE_COLS], dtype=float)


def macro_context_from_bars(qqq_bars: pd.DataFrame) -> tuple[str, float]:
    return macro_from_qqq_bars(qqq_bars)
