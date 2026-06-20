"""Household portfolio aggregation across linked broker accounts."""

from app.brokers.factory import get_broker
from app.core.config import settings
from app.db.storage import get_storage
from app.portfolio.demo import demo_portfolio


class PortfolioService:
    async def get_account_portfolio(self, broker_id: str, account_id: str) -> dict:
        if settings.multi_broker_enabled:
            try:
                broker = get_broker(broker_id)
                snap = await broker.get_portfolio_snapshot(account_id)
                if snap.get("positions"):
                    return snap
            except (ValueError, Exception):
                pass
        return demo_portfolio()

    async def get_household(self) -> dict:
        if not settings.multi_broker_enabled:
            single = demo_portfolio()
            return {
                "source": "demo",
                "account_count": 1,
                "total_value": single["account_value"],
                "total_daily_pnl": single["daily_pnl"],
                "accounts": [single],
                "positions": single["positions"],
                "sector_exposure": single["sector_exposure"],
            }

        storage = await get_storage()
        accounts = await storage.list_broker_accounts()
        snapshots: list[dict] = []
        merged_positions: dict[str, dict] = {}
        sector_totals: dict[str, float] = {}
        total_value = 0.0
        total_pnl = 0.0

        for account in accounts:
            try:
                broker = get_broker(account["broker_id"])
                snap = await broker.get_portfolio_snapshot(account["account_id"])
            except (ValueError, Exception):
                continue
            snap["account_label"] = account.get("label") or snap.get("account_label", account["account_id"])
            snap["account_type"] = account.get("account_type", "taxable")
            snapshots.append(snap)
            value = float(snap.get("account_value", 0))
            total_value += value
            total_pnl += float(snap.get("daily_pnl", 0))

        if not snapshots:
            single = demo_portfolio()
            return {
                "source": "demo",
                "account_count": 1,
                "total_value": single["account_value"],
                "total_daily_pnl": single["daily_pnl"],
                "accounts": [single],
                "positions": single["positions"],
                "sector_exposure": single["sector_exposure"],
            }

        for snap in snapshots:
            weight_scale = float(snap.get("account_value", 0)) / total_value if total_value else 0
            for ticker, pos in (snap.get("positions") or {}).items():
                shares = float(pos.get("shares", 0))
                weight = float(pos.get("weight_pct", 0)) * weight_scale
                sector = pos.get("sector", "Other")
                if ticker in merged_positions:
                    merged_positions[ticker]["shares"] += shares
                    merged_positions[ticker]["weight_pct"] += weight
                else:
                    merged_positions[ticker] = {
                        "shares": shares,
                        "weight_pct": weight,
                        "sector": sector,
                    }
                sector_totals[sector] = sector_totals.get(sector, 0) + weight

        for pos in merged_positions.values():
            pos["weight_pct"] = round(pos["weight_pct"], 2)

        sector_exposure = {k: round(v, 2) for k, v in sector_totals.items()}

        return {
            "source": "household",
            "account_count": len(snapshots),
            "total_value": round(total_value, 2),
            "total_daily_pnl": round(total_pnl, 2),
            "accounts": snapshots,
            "positions": merged_positions,
            "sector_exposure": sector_exposure,
        }
