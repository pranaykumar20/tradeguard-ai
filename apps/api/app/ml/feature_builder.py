"""Shared feature engineering — single source for training and inference."""

from __future__ import annotations

import numpy as np
import pandas as pd
import ta

FEATURE_COLS = [
    "price_vs_20dma",
    "price_vs_50dma",
    "rsi_14",
    "macd_signal",
    "atr_percent",
    "volume_spike",
    "news_sentiment_score",
    "qqq_trend_numeric",
    "vix_change",
    "regime_risk_adj",
]

TARGET_COL = "target_up_5d"


def qqq_trend_to_numeric(qqq_trend: str) -> float:
    return 1.0 if qqq_trend == "bullish" else 0.0


def macro_from_qqq_bars(qqq_bars: pd.DataFrame) -> tuple[str, float]:
    """Return QQQ trend label and VIX proxy from QQQ bars."""
    qqq_close = qqq_bars["close"]
    qqq_sma = qqq_close.rolling(20).mean().iloc[-1]
    qqq_last = float(qqq_close.iloc[-1])
    qqq_trend = "bullish" if qqq_last >= qqq_sma else "bearish"
    qqq_ret = qqq_close.pct_change().dropna()
    vix_change = float(qqq_ret.tail(5).std() * 100 * 10) if len(qqq_ret) > 5 else 2.0
    return qqq_trend, vix_change


def _compute_series(bars: pd.DataFrame) -> pd.DataFrame:
    close = bars["close"]
    high = bars["high"]
    low = bars["low"]
    volume = bars["volume"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    macd = ta.trend.MACD(close).macd_diff()
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    atr_pct = (atr / close.replace(0, np.nan)) * 100
    vol_mean = volume.rolling(20).mean()
    vol_spike = volume / vol_mean.replace(0, np.nan)

    return pd.DataFrame(
        {
            "price_vs_20dma": (close - sma20) / sma20.replace(0, np.nan) * 100,
            "price_vs_50dma": (close - sma50) / sma50.replace(0, np.nan) * 100,
            "rsi_14": rsi,
            "macd_signal": macd,
            "atr_percent": atr_pct,
            "volume_spike": vol_spike,
        }
    )


def build_training_frame(
    bars: pd.DataFrame,
    *,
    ticker: str = "",
    news_sentiment: float = 50.0,
    qqq_trend_numeric: float = 0.5,
    vix_change: float = 2.0,
    regime_risk_adj: float = 0.0,
) -> pd.DataFrame:
    """Build labeled rows for walk-forward training from OHLCV bars."""
    if len(bars) < 60:
        return pd.DataFrame()

    close = bars["close"]
    features = _compute_series(bars)
    target = (close.pct_change(5).shift(-5) > 0).astype(int)

    frame = features.copy()
    frame["news_sentiment_score"] = float(news_sentiment)
    frame["qqq_trend_numeric"] = float(qqq_trend_numeric)
    frame["vix_change"] = float(vix_change)
    frame["regime_risk_adj"] = float(regime_risk_adj)
    frame[TARGET_COL] = target
    if ticker:
        frame["ticker"] = ticker

    keep = FEATURE_COLS + [TARGET_COL]
    if ticker:
        keep.append("ticker")
    return frame[keep].dropna()


def latest_feature_row(
    bars: pd.DataFrame,
    *,
    news_sentiment: float = 50.0,
    qqq_trend: str = "bullish",
    vix_change: float = 2.0,
    regime_risk_adj: float = 0.0,
) -> dict[str, float]:
    """Latest feature values from bars (same formulas as training)."""
    if bars.empty:
        raise ValueError("bars must not be empty")

    features = _compute_series(bars)
    last = features.iloc[-1]
    close = bars["close"]
    last_price = float(close.iloc[-1])
    price_vs_20 = float(last["price_vs_20dma"]) if pd.notna(last["price_vs_20dma"]) else 0.0

    return {
        "last_price": round(last_price, 2),
        "price_vs_20dma": round(float(last["price_vs_20dma"]), 2) if pd.notna(last["price_vs_20dma"]) else 0.0,
        "price_vs_50dma": round(float(last["price_vs_50dma"]), 2) if pd.notna(last["price_vs_50dma"]) else 0.0,
        "rsi_14": round(float(last["rsi_14"]), 1) if pd.notna(last["rsi_14"]) else 50.0,
        "macd_signal": round(float(last["macd_signal"]), 2) if pd.notna(last["macd_signal"]) else 0.0,
        "atr_percent": round(float(last["atr_percent"]), 2) if pd.notna(last["atr_percent"]) else 0.0,
        "volume_spike": round(float(last["volume_spike"]), 2) if pd.notna(last["volume_spike"]) else 1.0,
        "news_sentiment_score": round(float(news_sentiment), 1),
        "qqq_trend": qqq_trend,
        "qqq_trend_numeric": qqq_trend_to_numeric(qqq_trend),
        "vix_change": round(float(vix_change), 1),
        "regime_risk_adj": round(float(regime_risk_adj), 1),
        "sector_strength": round(min(95, max(35, 55 + price_vs_20)), 0),
    }


def feature_vector_from_dict(features: dict) -> np.ndarray:
    """Build model input vector in FEATURE_COLS order."""
    return np.array([float(features[col]) for col in FEATURE_COLS], dtype=float)
