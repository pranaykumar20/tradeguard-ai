"""Mock traditional IRA broker — second adapter for household demos."""

from app.brokers.base import BrokerAdapter

_MOCK_QUOTES: dict[str, float] = {
    "NVDA": 140.0,
    "META": 520.0,
    "MSFT": 420.0,
    "QQQ": 480.0,
    "TSLA": 250.0,
    "GBTC": 85.0,
}


class MockIRABroker(BrokerAdapter):
    broker_id = "mock_ira"
    display_name = "Mock Traditional IRA"
    provider_name = "mock_ira"

    def __init__(self):
        self._orders: dict[str, dict] = {}

    @property
    def is_configured(self) -> bool:
        return True

    async def get_portfolio_snapshot(self, account_id: str | None = None) -> dict:
        return {
            "source": "mock_ira",
            "broker_id": self.broker_id,
            "account_id": account_id or "ira-traditional",
            "account_label": "Traditional IRA (mock)",
            "account_type": "ira",
            "account_value": 42_500.0,
            "buying_power": 0.0,
            "daily_pnl": 85.0,
            "daily_pnl_pct": 0.2,
            "beta": 1.05,
            "max_drawdown_est": -8.2,
            "diversification": "Balanced",
            "cash_pct": 5.0,
            "positions": {
                "QQQ": {"shares": 12, "weight_pct": 22.0, "sector": "Technology"},
                "MSFT": {"shares": 8, "weight_pct": 18.0, "sector": "Technology"},
                "META": {"shares": 4, "weight_pct": 12.0, "sector": "Technology"},
                "GBTC": {"shares": 20, "weight_pct": 8.0, "sector": "Technology"},
            },
            "sector_exposure": {
                "Technology": 60.0,
                "Communication": 0.0,
                "Healthcare": 0.0,
                "Other": 35.0,
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
            "provider": "mock_ira",
        }

    async def preview_order(self, order: dict) -> dict:
        ticker = order["ticker"].upper()
        quote = await self.get_quote(ticker)
        limit_price = float(order.get("limit_price") or quote["last_price"])
        qty = float(order["quantity"])
        return {
            "status": "preview_ok",
            "provider": "mock_ira",
            "broker_id": self.broker_id,
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
            return {"status": "rejected", "reason": "Manual approval required", "provider": "mock_ira"}
        preview = await self.preview_order(order)
        order_id = f"mock-ira-{len(self._orders) + 1:04d}"
        record = {**preview, "order_id": order_id, "status": "filled", "filled_at": "now"}
        self._orders[order_id] = record
        return record

    async def cancel_order(self, order_id: str) -> dict:
        if order_id in self._orders:
            self._orders[order_id]["status"] = "cancelled"
            return {"status": "cancelled", "order_id": order_id}
        return {"status": "not_found", "order_id": order_id}
