"""News and sentiment service — Phase 6.1 + Tavily web search."""

from dataclasses import asdict

from app.core.config import settings
from app.providers.news.factory import get_news_provider
from app.providers.news.tavily import TavilyNewsProvider


def format_news_for_context(news_data: dict | None) -> str:
    """Format Tavily headlines for LLM context."""
    if not news_data or not news_data.get("headlines"):
        return ""
    label = news_data.get("sentiment_label", "Neutral")
    provider = news_data.get("provider", "web")
    lines = [f"Live web search ({provider}, {label}):"]
    for headline in news_data["headlines"][:5]:
        title = headline.get("title", "")
        source = headline.get("source", "")
        summary = (headline.get("summary") or "").strip()
        lines.append(f"- {title} ({source})")
        if summary:
            lines.append(f"  {summary[:220]}")
    return "\n".join(lines)


class NewsService:
    def _tavily_provider(self) -> TavilyNewsProvider | None:
        if not settings.tavily_api_key:
            return None
        provider = get_news_provider()
        if isinstance(provider, TavilyNewsProvider):
            return provider
        return TavilyNewsProvider()

    def _news_payload(
        self,
        headlines: list,
        *,
        provider: str,
        query: str,
        ticker: str | None = None,
        live_search: bool = True,
    ) -> dict:
        if not headlines:
            return {
                "query": query,
                "ticker": ticker,
                "sentiment_score": 50.0,
                "sentiment_label": "Neutral",
                "headline_count": 0,
                "headlines": [],
                "provider": provider,
                "live_search": False,
            }

        avg = sum(h.sentiment for h in headlines) / len(headlines)
        if avg >= 62:
            label = "Bullish"
        elif avg <= 42:
            label = "Bearish"
        else:
            label = "Neutral"

        return {
            "query": query,
            "ticker": ticker,
            "sentiment_score": round(avg, 1),
            "sentiment_label": label,
            "headline_count": len(headlines),
            "headlines": [asdict(h) for h in headlines],
            "provider": provider,
            "live_search": live_search,
        }

    async def search_for_chat(
        self, message: str, *, ticker: str | None = None, limit: int = 5
    ) -> dict:
        """Tavily web search tailored to the user's chat question."""
        tavily = self._tavily_provider()
        if tavily is None:
            provider = get_news_provider()
            return {
                "query": message[:160],
                "ticker": ticker,
                "headline_count": 0,
                "headlines": [],
                "provider": provider.provider_name,
                "live_search": False,
                "hint": "Set TAVILY_API_KEY for live web search in chat",
            }

        trimmed = " ".join(message.split())[:160]
        if ticker:
            query = f"{ticker} stock news today: {trimmed}"
            headlines = await tavily.get_headlines(ticker, limit=limit)
            if not headlines:
                headlines = await tavily.search_query(query, limit=limit)
        else:
            query = f"{trimmed} US stock market investing news today"
            headlines = await tavily.search_query(query, limit=limit)
            if not headlines:
                headlines = await tavily.get_market_headlines(limit=limit)
                query = "US stock market today"

        return self._news_payload(
            headlines,
            provider="tavily",
            query=query,
            ticker=ticker,
            live_search=bool(headlines),
        )

    async def search_stock_price(self, ticker: str) -> dict:
        """Live web price lookup via Tavily (include_answer)."""
        tavily = self._tavily_provider()
        if tavily is None:
            return {"ticker": ticker.upper(), "answer": None, "provider": "none", "sources": []}
        return await tavily.search_stock_price(ticker)

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

    async def get_market_pulse(self, limit: int = 8) -> dict:
        """Broad market web search — Tavily when configured."""
        provider = get_news_provider()
        headlines: list = []
        if isinstance(provider, TavilyNewsProvider):
            headlines = await provider.get_market_headlines(limit=limit)

        if not headlines:
            return {
                "query": "US stock market today",
                "headline_count": 0,
                "headlines": [],
                "provider": provider.provider_name,
                "live_search": False,
                "hint": "Set TAVILY_API_KEY for real-time market web search",
            }

        avg = sum(h.sentiment for h in headlines) / len(headlines)
        if avg >= 62:
            label = "Risk-on headlines"
        elif avg <= 42:
            label = "Risk-off headlines"
        else:
            label = "Mixed market tone"

        return {
            "query": "US stock market today",
            "sentiment_score": round(avg, 1),
            "sentiment_label": label,
            "headline_count": len(headlines),
            "headlines": [asdict(h) for h in headlines],
            "provider": provider.provider_name,
            "live_search": True,
        }

    async def sentiment_score(self, ticker: str) -> float:
        data = await self.get_ticker_news(ticker, limit=6)
        return float(data["sentiment_score"])
