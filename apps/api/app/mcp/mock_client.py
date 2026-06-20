"""Mock Robinhood Agentic MCP — swap to live by setting ROBINHOOD_MCP_URL."""

from app.mcp.base import RobinhoodMCPClientBase

_MOCK_QUOTES: dict[str, float] = {
    "NVDA": 140.0,
    "META": 520.0,
    "MSFT": 420.0,
    "QQQ": 480.0,
    "TSLA": 250.0,
    "GBTC": 85.0,
}


class MockRobinhoodMCPClient(RobinhoodMCPClientBase):
    provider_name = "mock"

    def __init__(self):
        self._orders: dict[str, dict] = {}

    @property
    def is_configured(self) -> bool:
        return True

    async def get_portfolio_snapshot(self) -> dict:
        return {
            "source": "robinhood_mcp_mock",
            "account_type": "agentic",
            "account_value": 10_250.0,
            "buying_power": 2_100.0,
            "daily_pnl": -320.0,
            "daily_pnl_pct": -3.0,
            "beta": 1.22,
            "max_drawdown_est": -12.4,
            "diversification": "Moderate",
            "cash_pct": 20.0,
            "positions": {
                "NVDA": {"shares": 8, "weight_pct": 28.0, "sector": "Technology"},
                "META": {"shares": 5, "weight_pct": 18.0, "sector": "Technology"},
                "MSFT": {"shares": 4, "weight_pct": 14.0, "sector": "Technology"},
                "QQQ": {"shares": 3, "weight_pct": 12.0, "sector": "Technology"},
            },
            "sector_exposure": {
                "Technology": 72.0,
                "Communication": 8.0,
                "Healthcare": 0.0,
                "Other": 0.0,
            },
        }

    async def get_quote(self, ticker: str) -> dict:
        ticker = ticker.upper()
        last = _MOCK_QUOTES.get(ticker, 100.0)
        return {
            "ticker": ticker,
            "last_price": last,
            "bid": round(last * 0.999, 2),
            "ask": round(last * 1.001, 2),
            "provider": "mock_mcp",
        }

    async def preview_order(self, order: dict) -> dict:
        ticker = order["ticker"].upper()
        quote = await self.get_quote(ticker)
        limit_price = float(order.get("limit_price") or quote["last_price"])
        qty = float(order["quantity"])
        return {
            "status": "preview_ok",
            "provider": "mock_mcp",
            "ticker": ticker,
            "side": order["side"],
            "order_type": order.get("order_type", "limit"),
            "quantity": qty,
            "limit_price": limit_price,
            "estimated_cost": round(qty * limit_price, 2),
            "quote": quote,
        }

    async def place_order(self, order: dict, approved: bool = False) -> dict:
        if not approved:
            return {"status": "rejected", "reason": "Manual approval required", "provider": "mock_mcp"}

        preview = await self.preview_order(order)
        order_id = f"mock-rh-{len(self._orders) + 1:04d}"
        record = {
            **preview,
            "order_id": order_id,
            "status": "filled",
            "provider": "mock_mcp",
            "filled_at": "now",
        }
        self._orders[order_id] = record
        return record

    async def cancel_order(self, order_id: str) -> dict:
        if order_id in self._orders:
            self._orders[order_id]["status"] = "cancelled"
            return {"status": "cancelled", "order_id": order_id}
        return {"status": "not_found", "order_id": order_id}
