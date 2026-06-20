"""Deterministic mock market data — swap to Polygon by setting POLYGON_API_KEY."""

import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.providers.base import MarketDataProvider, QuoteSnapshot


def _seed(ticker: str, salt: str) -> float:
    digest = hashlib.sha256(f"{ticker}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class MockMarketDataProvider(MarketDataProvider):
    provider_name = "mock"

    async def get_daily_bars(self, ticker: str, days: int = 120) -> pd.DataFrame:
        ticker = ticker.upper()
        base = 80 + _seed(ticker, "base") * 400
        drift = (_seed(ticker, "drift") - 0.45) * 0.002
        vol = 0.012 + _seed(ticker, "vol") * 0.018

        end = date.today()
        rows = []
        price = base
        for i in range(days):
            d = end - timedelta(days=days - i - 1)
            shock = np.sin(i / 7 + _seed(ticker, "cycle") * 10) * vol
            ret = drift + shock
            open_p = price
            close_p = max(1.0, open_p * (1 + ret))
            high_p = max(open_p, close_p) * (1 + vol * 0.4)
            low_p = min(open_p, close_p) * (1 - vol * 0.4)
            volume = 1_000_000 * (0.8 + _seed(ticker, f"vol-{i}") * 0.8)
            rows.append(
                {
                    "date": d,
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(close_p, 2),
                    "volume": round(volume, 0),
                }
            )
            price = close_p

        return pd.DataFrame(rows)

    async def get_quote(self, ticker: str) -> QuoteSnapshot:
        df = await self.get_daily_bars(ticker, days=5)
        last = float(df.iloc[-1]["close"])
        prev = float(df.iloc[-2]["close"]) if len(df) > 1 else last
        change_pct = ((last - prev) / prev * 100) if prev else 0.0
        return QuoteSnapshot(
            ticker=ticker.upper(),
            last_price=last,
            change_pct=round(change_pct, 2),
            volume=float(df.iloc[-1]["volume"]),
        )
