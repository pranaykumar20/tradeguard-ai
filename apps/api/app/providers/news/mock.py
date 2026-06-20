"""Deterministic mock news headlines per ticker."""

import hashlib
from datetime import datetime, timedelta, timezone

from app.providers.news.base import NewsHeadline, NewsProvider

TEMPLATES = [
    ("{t} beats revenue expectations in latest quarter", 62),
    ("Analysts raise price target on {t} amid AI demand", 68),
    ("{t} faces regulatory scrutiny over market practices", 38),
    ("Institutional investors increase stake in {t}", 58),
    ("Supply chain concerns weigh on {t} near-term outlook", 42),
    ("{t} announces new product line expansion", 55),
    ("Sector rotation lifts {t} alongside tech peers", 60),
    ("Options activity spikes ahead of {t} earnings", 50),
]


def _seed(ticker: str, salt: str) -> float:
    digest = hashlib.sha256(f"{ticker}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class MockNewsProvider(NewsProvider):
    provider_name = "mock"

    async def get_headlines(self, ticker: str, limit: int = 8) -> list[NewsHeadline]:
        ticker = ticker.upper()
        headlines: list[NewsHeadline] = []
        now = datetime.now(timezone.utc)
        for i, (template, base_sentiment) in enumerate(TEMPLATES[:limit]):
            jitter = (_seed(ticker, f"news-{i}") - 0.5) * 20
            sentiment = max(5.0, min(95.0, base_sentiment + jitter))
            published = now - timedelta(hours=int(6 + i * 7 + _seed(ticker, f"h-{i}") * 12))
            headlines.append(
                NewsHeadline(
                    title=template.format(t=ticker),
                    summary=f"Mock headline for {ticker} — swap NEWS_PROVIDER for live feeds.",
                    source="TradeGuard Mock Wire",
                    published_at=published.isoformat(),
                    sentiment=round(sentiment, 1),
                )
            )
        return headlines
