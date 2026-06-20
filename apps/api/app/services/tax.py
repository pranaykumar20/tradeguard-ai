"""Tax lot tracking and wash-sale awareness."""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.storage import get_storage


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TaxService:
    async def list_lots(
        self, ticker: str | None = None, account_id: str | None = None
    ) -> list[dict]:
        storage = await get_storage()
        return await storage.list_tax_lots(ticker=ticker, account_id=account_id)

    async def analyze_sell(
        self,
        ticker: str,
        quantity: float,
        limit_price: float,
        account_id: str | None = None,
    ) -> dict:
        if not settings.tax_lot_tracking_enabled:
            return {"enabled": False, "warnings": [], "blocks": [], "lots_selected": []}

        storage = await get_storage()
        lots = await storage.list_tax_lots(ticker=ticker.upper(), account_id=account_id)
        warnings: list[str] = []
        blocks: list[str] = []
        selected: list[dict] = []
        remaining = quantity
        now = datetime.now(timezone.utc)
        window = timedelta(days=settings.wash_sale_window_days)

        for lot in sorted(lots, key=lambda row: _parse_dt(row["acquired_at"])):
            if remaining <= 0:
                break
            take = min(remaining, float(lot["quantity"]))
            cost = float(lot["cost_basis"])
            gain = (limit_price - cost) * take
            acquired = _parse_dt(lot["acquired_at"])
            lot_info = {
                "lot_id": lot["id"],
                "quantity": take,
                "cost_basis": cost,
                "estimated_gain": round(gain, 2),
                "acquired_at": lot["acquired_at"],
            }
            selected.append(lot_info)

            if gain < 0 and (now - acquired) <= window:
                warnings.append(
                    f"Lot acquired {acquired.date()} may trigger wash-sale rules if repurchased "
                    f"within {settings.wash_sale_window_days} days."
                )
            if lot.get("account_type") == "ira" or lot.get("broker_id") == "mock_ira":
                warnings.append("IRA sells have tax-deferred treatment — lot selection is informational.")

            remaining -= take

        if remaining > 0:
            warnings.append(f"No tax lots cover {remaining:.2f} shares — using estimated cost basis.")

        total_gain = sum(l["estimated_gain"] for l in selected)
        return {
            "enabled": True,
            "ticker": ticker.upper(),
            "quantity": quantity,
            "limit_price": limit_price,
            "estimated_total_gain": round(total_gain, 2),
            "warnings": warnings,
            "blocks": blocks,
            "lots_selected": selected,
        }

    async def enrich_strategy_proposal(
        self, ticker: str, side: str, quantity: float, limit_price: float | None
    ) -> dict:
        if side != "sell" or not limit_price:
            return {}
        return await self.analyze_sell(ticker, quantity, limit_price)
