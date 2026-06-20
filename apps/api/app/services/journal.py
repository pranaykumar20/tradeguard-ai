"""Paper trade journal service."""

from app.core.config import settings
from app.db.storage import get_storage
from app.risk.engine import RiskEngine


class JournalService:
    def __init__(self):
        self.risk = RiskEngine()

    async def create_trade_plan(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float,
        reason: str = "",
    ) -> dict:
        preview = await self.risk.preview_trade(
            ticker=ticker.upper(),
            side=side,
            quantity=quantity,
            limit_price=limit_price,
        )
        storage = await get_storage()
        trade = await storage.create_paper_trade(
            {
                "ticker": ticker.upper(),
                "side": side,
                "quantity": quantity,
                "limit_price": limit_price,
                "fill_price": None,
                "status": "planned" if preview["allowed"] else "rejected",
                "verdict": preview["verdict"],
                "reason": reason or "; ".join(preview.get("blocks") or preview.get("warnings") or []),
                "pnl": None,
            }
        )
        return {"trade": trade, "preview": preview}

    async def fill_trade(self, trade_id: str, fill_price: float | None = None) -> dict:
        storage = await get_storage()
        trades = await storage.list_paper_trades(limit=500)
        trade = next((t for t in trades if t["id"] == trade_id), None)
        if not trade:
            raise ValueError("Trade not found")

        price = fill_price or trade["limit_price"]
        direction = 1 if trade["side"] == "buy" else -1
        pnl = round(direction * trade["quantity"] * price * 0.012, 2)

        updated = await storage.update_paper_trade(
            trade_id,
            {"fill_price": price, "status": "filled", "pnl": pnl},
        )
        if not updated:
            raise ValueError("Trade not found")
        return updated

    async def list_trades(self, limit: int = 100) -> list[dict]:
        storage = await get_storage()
        return await storage.list_paper_trades(limit=limit)

    async def stats(self) -> dict:
        storage = await get_storage()
        return await storage.paper_trade_stats()
