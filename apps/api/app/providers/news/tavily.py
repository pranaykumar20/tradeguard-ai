"""Tavily web search — real-time market news via search API."""

from datetime import datetime, timezone

import httpx
import structlog

from app.core.config import settings
from app.providers.news.base import NewsHeadline, NewsProvider
from app.providers.news.mock import MockNewsProvider
from app.providers.news.sentiment import sentiment_from_text

logger = structlog.get_logger()

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyNewsProvider(NewsProvider):
    provider_name = "tavily"

    def __init__(self):
        self._fallback = MockNewsProvider()

    async def _search(self, query: str, limit: int = 8) -> list[NewsHeadline]:
        if not settings.tavily_api_key:
            return []

        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "topic": "news",
            "search_depth": settings.tavily_search_depth,
            "max_results": min(limit, 20),
            "days": settings.tavily_news_days,
            "include_answer": False,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(TAVILY_SEARCH_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()

            headlines: list[NewsHeadline] = []
            for item in data.get("results") or []:
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                summary = (item.get("content") or title)[:280]
                text = f"{title} {summary}"
                published = item.get("published_date") or datetime.now(timezone.utc).isoformat()
                headlines.append(
                    NewsHeadline(
                        title=title,
                        summary=summary,
                        source=self._source_from_url(item.get("url", "")),
                        published_at=published,
                        sentiment=round(sentiment_from_text(text), 1),
                        url=item.get("url", ""),
                    )
                )
            return headlines[:limit]
        except Exception as exc:
            logger.warning("tavily_search_failed", query=query, error=str(exc))
            return []

    @staticmethod
    def _source_from_url(url: str) -> str:
        if not url:
            return "Tavily"
        try:
            host = url.split("//", 1)[1].split("/", 1)[0]
            return host.removeprefix("www.")
        except IndexError:
            return "Tavily"

    async def get_headlines(self, ticker: str, limit: int = 8) -> list[NewsHeadline]:
        ticker = ticker.upper()
        query = (
            f"{ticker} stock news today earnings analyst price target "
            f"market sentiment breaking"
        )
        headlines = await self._search(query, limit=limit)
        if headlines:
            return headlines
        return await self._fallback.get_headlines(ticker, limit=limit)

    async def get_market_headlines(self, limit: int = 8) -> list[NewsHeadline]:
        query = (
            "US stock market news today S&P 500 Nasdaq Dow Fed rates "
            "earnings macro volatility"
        )
        return await self._search(query, limit=limit)

    async def search_query(self, query: str, limit: int = 8) -> list[NewsHeadline]:
        """Run a custom Tavily news search (used by chat agent)."""
        return await self._search(query, limit=limit)
