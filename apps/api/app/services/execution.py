"""Guarded trade execution — risk gate, broker preview, manual approval."""

from datetime import datetime, timezone

from app.brokers.factory import get_broker
from app.core.config import settings
from app.db.storage import get_storage
from app.mcp.factory import is_mcp_live_for_user
from app.portfolio.demo import demo_portfolio
from app.risk.engine import RiskEngine
from app.services.monitoring import MonitoringService
from app.services.portfolio import PortfolioService
from app.services.tax import TaxService


class ExecutionService:
    def __init__(self):
        self.risk = RiskEngine()
        self.monitoring = MonitoringService()
        self.portfolio_service = PortfolioService()
        self.tax = TaxService()

    def _resolve_broker(self, broker_id: str | None):
        bid = broker_id or settings.default_broker_id
        return get_broker(bid), bid

    async def _trading_halt_block(self) -> str | None:
        halted, reason = await self.monitoring.is_trading_halted()
        if halted:
            return f"Trading halted: {reason}"
        return None

    async def _portfolio_for_risk(
        self, broker_id: str | None = None, account_id: str | None = None
    ) -> dict:
        if settings.multi_broker_enabled and broker_id and account_id:
            try:
                snap = await self.portfolio_service.get_account_portfolio(broker_id, account_id)
                if snap.get("positions"):
                    return snap
            except Exception:
                pass
        if settings.robinhood_mcp_enabled or await is_mcp_live_for_user():
            try:
                broker, bid = self._resolve_broker(settings.default_broker_id)
                snap = await broker.get_portfolio_snapshot(account_id)
                if snap.get("positions"):
                    return snap
            except Exception:
                pass
        if settings.multi_broker_enabled:
            household = await self.portfolio_service.get_household()
            if household.get("positions"):
                return {
                    "account_value": household["total_value"],
                    "daily_pnl": household["total_daily_pnl"],
                    "positions": household["positions"],
                    "sector_exposure": household["sector_exposure"],
                }
        return demo_portfolio()

    async def get_quote(self, ticker: str, broker_id: str | None = None) -> dict:
        broker, _ = self._resolve_broker(broker_id)
        return await broker.get_quote(ticker.upper())

    async def preview_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float | None = None,
        order_type: str = "limit",
        asset_type: str = "equity",
        broker_id: str | None = None,
        account_id: str | None = None,
        option_contract: dict | None = None,
    ) -> dict:
        ticker = ticker.upper()
        broker, bid = self._resolve_broker(broker_id)
        acct = account_id or ("agentic-main" if bid == "robinhood_agentic" else "ira-traditional")
        portfolio = await self._portfolio_for_risk(broker_id=bid, account_id=acct)

        if limit_price is None:
            quote = await broker.get_quote(ticker)
            limit_price = float(quote.get("last_price") or quote.get("ask") or 0)

        order = {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "limit_price": limit_price,
            "order_type": order_type,
            "asset_type": asset_type,
            "broker_id": bid,
            "account_id": acct,
            "option_contract": option_contract,
        }

        halt_block = await self._trading_halt_block()
        risk_preview = await self.risk.preview_trade(
            ticker=ticker,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_type=order_type,
            asset_type=asset_type,
            portfolio=portfolio,
            option_contract=option_contract,
        )
        if halt_block:
            risk_preview["blocks"] = list(risk_preview.get("blocks", [])) + [halt_block]
            risk_preview["allowed"] = False
            risk_preview["verdict"] = "BLOCK"

        tax_analysis = {}
        if side == "sell" and settings.tax_lot_tracking_enabled:
            tax_analysis = await self.tax.analyze_sell(ticker, quantity, limit_price, account_id=acct)
            if tax_analysis.get("warnings"):
                risk_preview["warnings"] = list(risk_preview.get("warnings", [])) + tax_analysis["warnings"]
                if risk_preview["allowed"] and tax_analysis["warnings"]:
                    risk_preview["verdict"] = "CAUTION"

        broker_preview = await broker.preview_order(order)

        return {
            "risk": risk_preview,
            "broker": broker_preview,
            "mcp": broker_preview,
            "order": order,
            "broker_id": bid,
            "broker_provider": broker.provider_name if hasattr(broker, "provider_name") else bid,
            "mcp_provider": getattr(broker, "provider_name", bid),
            "tax": tax_analysis,
        }

    async def submit_for_approval(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float | None = None,
        order_type: str = "limit",
        notes: str = "",
        asset_type: str = "equity",
        broker_id: str | None = None,
        account_id: str | None = None,
        option_contract: dict | None = None,
    ) -> dict:
        if asset_type == "option" and not settings.options_workflow_enabled:
            return {
                "status": "blocked",
                "reason": "Options workflow is disabled",
                "preview": None,
            }

        preview = await self.preview_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_type=order_type,
            asset_type=asset_type,
            broker_id=broker_id,
            account_id=account_id,
            option_contract=option_contract,
        )
        risk = preview["risk"]
        if not risk["allowed"]:
            await self.monitoring.notify_block(ticker.upper(), risk.get("blocks", []))
            return {
                "status": "blocked",
                "reason": "; ".join(risk["blocks"]),
                "preview": preview,
            }

        storage = await get_storage()
        bid = preview["broker_id"]
        acct = preview["order"]["account_id"]
        request = await storage.create_approval_request(
            {
                "ticker": ticker.upper(),
                "side": side,
                "quantity": quantity,
                "limit_price": preview["order"]["limit_price"],
                "order_type": order_type,
                "asset_type": asset_type,
                "broker_id": bid,
                "account_id": acct,
                "option_contract": option_contract,
                "status": "pending",
                "risk_preview": risk,
                "mcp_preview": preview["broker"],
                "execution_result": None,
                "order_id": None,
                "notes": notes,
            }
        )
        if settings.push_notifications_enabled:
            from app.services.push import PushNotificationService

            await PushNotificationService().notify(
                title=f"Approval needed — {ticker.upper()}",
                body=f"{side.upper()} {quantity} @ ${preview['order']['limit_price']:.2f} · {risk.get('verdict', '—')}",
                event_type="pending_approval",
                severity="high",
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

        asset_type = req.get("asset_type", "equity")
        if asset_type == "option" and not settings.options_workflow_enabled:
            raise ValueError("Options workflow is disabled")

        portfolio = await self._portfolio_for_risk(
            broker_id=req.get("broker_id"), account_id=req.get("account_id")
        )
        risk = await self.risk.preview_trade(
            ticker=req["ticker"],
            side=req["side"],
            quantity=req["quantity"],
            limit_price=req["limit_price"],
            order_type=req.get("order_type", "limit"),
            asset_type=asset_type,
            portfolio=portfolio,
            option_contract=req.get("option_contract"),
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

        submit_snapshot = (req.get("risk_preview") or {}).get("ml_snapshot")
        if submit_snapshot:
            risk["ml_snapshot"] = submit_snapshot

        broker, _ = self._resolve_broker(req.get("broker_id"))
        order = {
            "ticker": req["ticker"],
            "side": req["side"],
            "quantity": req["quantity"],
            "limit_price": req["limit_price"],
            "order_type": req.get("order_type", "limit"),
            "asset_type": asset_type,
            "option_contract": req.get("option_contract"),
        }
        result = await broker.place_order(order, approved=True)

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
                "approval_id": request_id,
                "source": "execution",
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
