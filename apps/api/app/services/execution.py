"""Guarded trade execution — risk gate, MCP preview, manual approval."""

from datetime import datetime, timezone

from app.core.config import settings
from app.db.storage import get_storage
from app.mcp.factory import get_mcp_client
from app.portfolio.demo import demo_portfolio
from app.risk.engine import RiskEngine


class ExecutionService:
    def __init__(self):
        self.risk = RiskEngine()
        self.mcp = get_mcp_client()

    async def _portfolio_for_risk(self) -> dict:
        if settings.robinhood_mcp_enabled:
            try:
                snap = await self.mcp.get_portfolio_snapshot()
                if snap.get("positions"):
                    return snap
            except Exception:
                pass
        return demo_portfolio()

    async def get_quote(self, ticker: str) -> dict:
        return await self.mcp.get_quote(ticker.upper())

    async def preview_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float | None = None,
        order_type: str = "limit",
    ) -> dict:
        ticker = ticker.upper()
        portfolio = await self._portfolio_for_risk()

        if limit_price is None:
            quote = await self.mcp.get_quote(ticker)
            limit_price = float(quote.get("last_price") or quote.get("ask") or 0)

        order = {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "limit_price": limit_price,
            "order_type": order_type,
        }

        risk_preview = await self.risk.preview_trade(
            ticker=ticker,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_type=order_type,
            portfolio=portfolio,
        )
        mcp_preview = await self.mcp.preview_order(order)

        return {
            "risk": risk_preview,
            "mcp": mcp_preview,
            "order": order,
            "mcp_provider": self.mcp.provider_name,
        }

    async def submit_for_approval(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float | None = None,
        order_type: str = "limit",
        notes: str = "",
    ) -> dict:
        preview = await self.preview_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_type=order_type,
        )
        risk = preview["risk"]
        if not risk["allowed"]:
            return {
                "status": "blocked",
                "reason": "; ".join(risk["blocks"]),
                "preview": preview,
            }

        storage = await get_storage()
        request = await storage.create_approval_request(
            {
                "ticker": ticker.upper(),
                "side": side,
                "quantity": quantity,
                "limit_price": preview["order"]["limit_price"],
                "order_type": order_type,
                "status": "pending",
                "risk_preview": risk,
                "mcp_preview": preview["mcp"],
                "execution_result": None,
                "order_id": None,
                "notes": notes,
            }
        )
        return {"status": "pending", "approval": request, "preview": preview}

    async def list_approvals(self, status: str | None = None, limit: int = 50) -> list[dict]:
        storage = await get_storage()
        return await storage.list_approval_requests(status=status, limit=limit)

    async def get_approval(self, request_id: str) -> dict | None:
        storage = await get_storage()
        return await storage.get_approval_request(request_id)

    async def approve(self, request_id: str) -> dict:
        storage = await get_storage()
        req = await storage.get_approval_request(request_id)
        if not req:
            raise ValueError("Approval request not found")
        if req["status"] != "pending":
            raise ValueError(f"Request already {req['status']}")

        portfolio = await self._portfolio_for_risk()
        risk = await self.risk.preview_trade(
            ticker=req["ticker"],
            side=req["side"],
            quantity=req["quantity"],
            limit_price=req["limit_price"],
            order_type=req.get("order_type", "limit"),
            portfolio=portfolio,
        )
        if not risk["allowed"]:
            await storage.update_approval_request(
                request_id,
                {
                    "status": "rejected",
                    "notes": "; ".join(risk["blocks"]),
                    "resolved_at": datetime.now(timezone.utc),
                },
            )
            raise ValueError("Risk blocks changed — order rejected: " + "; ".join(risk["blocks"]))

        order = {
            "ticker": req["ticker"],
            "side": req["side"],
            "quantity": req["quantity"],
            "limit_price": req["limit_price"],
            "order_type": req.get("order_type", "limit"),
        }
        result = await self.mcp.place_order(order, approved=True)

        await storage.create_paper_trade(
            {
                "ticker": req["ticker"],
                "side": req["side"],
                "quantity": req["quantity"],
                "limit_price": req["limit_price"],
                "fill_price": req["limit_price"],
                "status": "filled",
                "verdict": risk["verdict"],
                "reason": req.get("notes") or "Approved via execution flow",
                "pnl": None,
            }
        )

        updated = await storage.update_approval_request(
            request_id,
            {
                "status": "executed",
                "execution_result": result,
                "order_id": result.get("order_id"),
                "resolved_at": datetime.now(timezone.utc),
            },
        )
        return {"status": "executed", "approval": updated, "execution": result}

    async def reject(self, request_id: str, reason: str = "") -> dict:
        storage = await get_storage()
        req = await storage.get_approval_request(request_id)
        if not req:
            raise ValueError("Approval request not found")
        if req["status"] != "pending":
            raise ValueError(f"Request already {req['status']}")

        updated = await storage.update_approval_request(
            request_id,
            {
                "status": "rejected",
                "notes": reason or "Rejected by user",
                "resolved_at": datetime.now(timezone.utc),
            },
        )
        return {"status": "rejected", "approval": updated}
