"""News provider factory."""

from app.core.config import settings
from app.providers.news.base import NewsProvider
from app.providers.news.mock import MockNewsProvider
from app.providers.news.polygon import PolygonNewsProvider

_provider: NewsProvider | None = None


def get_news_provider() -> NewsProvider:
    global _provider
    if _provider is None:
        if settings.use_polygon_news:
            _provider = PolygonNewsProvider()
        else:
            _provider = MockNewsProvider()
    return _provider


def reset_news_provider() -> None:
    global _provider
    _provider = None
