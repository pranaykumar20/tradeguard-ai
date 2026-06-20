"""Live stock quotes for chat — market data provider + Tavily web fallback."""

import structlog

from app.providers.market.factory import get_market_data_provider
from app.services.news import NewsService

logger = structlog.get_logger()
_news = NewsService()


async def fetch_quote(ticker: str) -> dict:
    """Latest price from Polygon (if configured) or mock market data."""
    ticker = ticker.upper()
    try:
        provider = get_market_data_provider()
        snap = await provider.get_quote(ticker)
        return {
            "ticker": snap.ticker,
            "last_price": snap.last_price,
            "change_pct": snap.change_pct,
            "volume": snap.volume,
            "provider": provider.provider_name,
            "live": provider.provider_name == "polygon",
        }
    except Exception as exc:
        logger.warning("quote_fetch_failed", ticker=ticker, error=str(exc))
        return {
            "ticker": ticker,
            "last_price": None,
            "change_pct": None,
            "volume": None,
            "provider": "unknown",
            "live": False,
        }


async def fetch_price_context(ticker: str, *, include_web: bool = True) -> tuple[dict, str]:
    """Fetch quote + optional Tavily price search; return data and LLM context block."""
    quote = await fetch_quote(ticker)
    web_price: dict = {}

    if include_web:
        try:
            web_price = await _news.search_stock_price(ticker)
        except Exception as exc:
            logger.warning("tavily_price_search_failed", ticker=ticker, error=str(exc))

    return quote, format_price_for_context(quote, web_price)


def format_price_for_context(quote: dict, web_price: dict | None = None) -> str:
    lines: list[str] = []
    if quote.get("last_price") is not None:
        live_label = "live" if quote.get("live") else "simulated"
        lines.append(
            f"Stock quote ({quote.get('provider', 'market')}, {live_label}): "
            f"{quote['ticker']} ${quote['last_price']:.2f} "
            f"({quote.get('change_pct', 0):+.2f}% vs prior session)"
        )
        if quote.get("volume"):
            lines.append(f"  Volume: {int(quote['volume']):,}")

    if web_price:
        answer = (web_price.get("answer") or "").strip()
        if answer:
            lines.append(f"Web search ({web_price.get('provider', 'tavily')}): {answer}")
        for item in (web_price.get("sources") or [])[:2]:
            title = item.get("title", "")
            url = item.get("url", "")
            if title:
                lines.append(f"  - {title}" + (f" ({url})" if url else ""))

    return "\n".join(lines)


def quote_to_dict(quote: dict) -> dict:
    return {k: quote.get(k) for k in ("ticker", "last_price", "change_pct", "volume", "provider", "live")}
