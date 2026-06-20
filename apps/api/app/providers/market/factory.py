"""Market data provider factory."""

from app.core.config import settings
from app.providers.base import MarketDataProvider
from app.providers.market.mock import MockMarketDataProvider
from app.providers.market.polygon import PolygonMarketDataProvider

_provider: MarketDataProvider | None = None


def get_market_data_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        if settings.use_polygon:
            _provider = PolygonMarketDataProvider()
        else:
            _provider = MockMarketDataProvider()
    return _provider
