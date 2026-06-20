"""News provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NewsHeadline:
    title: str
    summary: str
    source: str
    published_at: str
    sentiment: float  # 0–100, 50 = neutral
    url: str = ""


class NewsProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def get_headlines(self, ticker: str, limit: int = 8) -> list[NewsHeadline]:
        pass
