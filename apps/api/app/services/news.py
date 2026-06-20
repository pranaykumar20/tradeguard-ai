"""News and sentiment service — Phase 6.1."""

from dataclasses import asdict

from app.core.config import settings
from app.providers.news.factory import get_news_provider


class NewsService:
    async def get_ticker_news(self, ticker: str, limit: int = 8) -> dict:
        provider = get_news_provider()
        headlines = await provider.get_headlines(ticker.upper(), limit=limit)
        if not headlines:
            return {
                "ticker": ticker.upper(),
                "sentiment_score": 50.0,
                "sentiment_label": "Neutral",
                "headline_count": 0,
                "headlines": [],
                "provider": provider.provider_name,
            }

        avg = sum(h.sentiment for h in headlines) / len(headlines)
        if avg >= 62:
            label = "Bullish"
        elif avg <= 42:
            label = "Bearish"
        else:
            label = "Neutral"

        return {
            "ticker": ticker.upper(),
            "sentiment_score": round(avg, 1),
            "sentiment_label": label,
            "headline_count": len(headlines),
            "headlines": [asdict(h) for h in headlines],
            "provider": provider.provider_name,
        }

    async def sentiment_score(self, ticker: str) -> float:
        data = await self.get_ticker_news(ticker, limit=6)
        return float(data["sentiment_score"])
