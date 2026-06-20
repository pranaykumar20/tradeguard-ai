"""Robinhood MCP client interface."""

from abc import ABC, abstractmethod


class RobinhoodMCPClientBase(ABC):
    provider_name: str = "base"

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def get_portfolio_snapshot(self) -> dict:
        pass

    @abstractmethod
    async def get_quote(self, ticker: str) -> dict:
        pass

    @abstractmethod
    async def preview_order(self, order: dict) -> dict:
        pass

    @abstractmethod
    async def place_order(self, order: dict, approved: bool = False) -> dict:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict:
        pass
