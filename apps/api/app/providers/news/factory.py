"""News provider factory."""

from app.core.config import settings
from app.providers.news.base import NewsProvider
from app.providers.news.mock import MockNewsProvider
from app.providers.news.polygon import PolygonNewsProvider
from app.providers.news.tavily import TavilyNewsProvider

_provider: NewsProvider | None = None


def get_news_provider() -> NewsProvider:
    global _provider
    if _provider is None:
        mode = settings.news_provider.lower()
        if mode == "mock":
            _provider = MockNewsProvider()
        elif mode == "tavily":
            _provider = TavilyNewsProvider()
        elif mode == "polygon":
            _provider = PolygonNewsProvider()
        elif settings.tavily_api_key:
            _provider = TavilyNewsProvider()
        elif settings.polygon_api_key:
            _provider = PolygonNewsProvider()
        else:
            _provider = MockNewsProvider()
    return _provider


def reset_news_provider() -> None:
    global _provider
    _provider = None
