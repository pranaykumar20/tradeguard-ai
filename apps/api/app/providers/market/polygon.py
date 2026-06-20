"""Polygon.io market data — activated when POLYGON_API_KEY is set."""

import httpx
import pandas as pd

from app.core.config import settings
from app.providers.base import MarketDataProvider, QuoteSnapshot
from app.providers.market.mock import MockMarketDataProvider


class PolygonMarketDataProvider(MarketDataProvider):
    provider_name = "polygon"

    def __init__(self):
        self._fallback = MockMarketDataProvider()

    async def get_daily_bars(self, ticker: str, days: int = 120) -> pd.DataFrame:
        if not settings.polygon_api_key:
            return await self._fallback.get_daily_bars(ticker, days=days)

        url = (
            f"{settings.polygon_base_url}/v2/aggs/ticker/{ticker.upper()}/range/1/day/"
            f"{days}d/now"
        )
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    url,
                    params={"adjusted": "true", "sort": "asc", "apiKey": settings.polygon_api_key},
                )
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results") or []
            if not results:
                return await self._fallback.get_daily_bars(ticker, days=days)

            rows = []
            for bar in results[-days:]:
                rows.append(
                    {
                        "date": pd.to_datetime(bar["t"], unit="ms").date(),
                        "open": bar["o"],
                        "high": bar["h"],
                        "low": bar["l"],
                        "close": bar["c"],
                        "volume": bar["v"],
                    }
                )
            return pd.DataFrame(rows)
        except Exception:
            return await self._fallback.get_daily_bars(ticker, days=days)

    async def get_quote(self, ticker: str) -> QuoteSnapshot:
        ticker = ticker.upper()
        if settings.polygon_api_key:
            url = (
                f"{settings.polygon_base_url}/v2/snapshot/locale/us/markets/stocks/"
                f"tickers/{ticker}"
            )
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url, params={"apiKey": settings.polygon_api_key})
                    resp.raise_for_status()
                    data = resp.json()
                tick = (data.get("ticker") or {})
                last_trade = tick.get("lastTrade") or {}
                day = tick.get("day") or {}
                prev = tick.get("prevDay") or {}
                last = float(last_trade.get("p") or day.get("c") or 0)
                if last <= 0:
                    raise ValueError("empty snapshot price")
                prev_close = float(prev.get("c") or last)
                change_pct = tick.get("todaysChangePerc")
                if change_pct is None and prev_close:
                    change_pct = ((last - prev_close) / prev_close) * 100
                volume = float(day.get("v") or 0)
                return QuoteSnapshot(
                    ticker=ticker,
                    last_price=round(last, 2),
                    change_pct=round(float(change_pct or 0), 2),
                    volume=volume,
                )
            except Exception:
                pass

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
