"""Polygon.io news — activated when POLYGON_API_KEY is set."""

import httpx

from app.core.config import settings
from app.providers.news.base import NewsHeadline, NewsProvider
from app.providers.news.mock import MockNewsProvider


def _sentiment_from_text(text: str) -> float:
    positive = {"beat", "raise", "growth", "surge", "record", "buy", "strong", "gain"}
    negative = {"miss", "cut", "fall", "drop", "weak", "loss", "risk", "probe", "lawsuit"}
    words = set(text.lower().split())
    score = 50.0
    score += 8 * len(words & positive)
    score -= 8 * len(words & negative)
    return max(5.0, min(95.0, score))


class PolygonNewsProvider(NewsProvider):
    provider_name = "polygon"

    def __init__(self):
        self._fallback = MockNewsProvider()

    async def get_headlines(self, ticker: str, limit: int = 8) -> list[NewsHeadline]:
        if not settings.polygon_api_key:
            return await self._fallback.get_headlines(ticker, limit=limit)

        url = f"{settings.polygon_base_url}/v2/reference/news"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    params={
                        "ticker": ticker.upper(),
                        "limit": limit,
                        "apiKey": settings.polygon_api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results") or []
            if not results:
                return await self._fallback.get_headlines(ticker, limit=limit)

            headlines: list[NewsHeadline] = []
            for item in results[:limit]:
                title = item.get("title") or ""
                desc = item.get("description") or title
                text = f"{title} {desc}"
                headlines.append(
                    NewsHeadline(
                        title=title,
                        summary=desc[:280],
                        source=item.get("publisher", {}).get("name", "Polygon"),
                        published_at=item.get("published_utc", ""),
                        sentiment=round(_sentiment_from_text(text), 1),
                        url=item.get("article_url", ""),
                    )
                )
            return headlines
        except Exception:
            return await self._fallback.get_headlines(ticker, limit=limit)
