"""External API provider interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class QuoteSnapshot:
    ticker: str
    last_price: float
    change_pct: float
    volume: float


class MarketDataProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def get_daily_bars(self, ticker: str, days: int = 120) -> pd.DataFrame:
        """Return OHLCV dataframe with columns: date, open, high, low, close, volume."""

    @abstractmethod
    async def get_quote(self, ticker: str) -> QuoteSnapshot:
        pass

    async def get_macro_bars(self, ticker: str, days: int = 60) -> pd.DataFrame:
        return await self.get_daily_bars(ticker, days=days)


class EmbeddingProvider(ABC):
    provider_name: str = "base"
    dimensions: int = 1536

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]
