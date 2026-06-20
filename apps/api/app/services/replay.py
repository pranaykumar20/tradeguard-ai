"""Trade replay — assemble decision → risk → execution timeline."""

from datetime import datetime, timezone

from app.db.storage import get_storage


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ReplayService:
    async def replay_approval(self, approval_id: str) -> dict:
        storage = await get_storage()
        approval = await storage.get_approval_request(approval_id)
        if not approval:
            raise ValueError("Approval not found")

        events: list[dict] = []
        proposals = [
            p
            for p in await storage.list_strategy_proposals(limit=200)
            if p.get("approval_id") == approval_id
        ]
        for proposal in proposals:
            events.append(
                {
                    "step": "strategy_proposal",
                    "at": proposal.get("created_at"),
                    "title": f"Strategy: {proposal.get('strategy_name')}",
                    "detail": proposal.get("trigger_reason") or proposal.get("status", ""),
                    "data": proposal,
                }
            )

        events.append(
            {
                "step": "submitted",
                "at": approval.get("created_at"),
                "title": "Order submitted for approval",
                "detail": f"{approval['side'].upper()} {approval['quantity']} {approval['ticker']}",
                "data": {
                    "broker_id": approval.get("broker_id"),
                    "account_id": approval.get("account_id"),
                    "asset_type": approval.get("asset_type", "equity"),
                },
            }
        )

        risk = approval.get("risk_preview") or {}
        if risk:
            events.append(
                {
                    "step": "risk_evaluated",
                    "at": approval.get("created_at"),
                    "title": f"Risk verdict: {risk.get('verdict', '—')}",
                    "detail": "; ".join(risk.get("blocks") or risk.get("warnings") or []) or "Passed risk checks",
                    "data": risk,
                }
            )

        broker_preview = approval.get("mcp_preview") or {}
        if broker_preview:
            events.append(
                {
                    "step": "broker_preview",
                    "at": approval.get("created_at"),
                    "title": "Broker preview",
                    "detail": broker_preview.get("status", "preview_ok"),
                    "data": broker_preview,
                }
            )

        ticker = approval.get("ticker", "")
        created = _parse_dt(approval.get("created_at"))
        audit_rows = await storage.list_automation_audit(limit=100)
        for entry in audit_rows:
            if entry.get("ticker") and entry["ticker"] != ticker:
                continue
            entry_at = _parse_dt(entry.get("created_at"))
            if created and entry_at and abs((entry_at - created).total_seconds()) > 3600:
                continue
            events.append(
                {
                    "step": "automation_audit",
                    "at": entry.get("created_at"),
                    "title": entry.get("event_type", "automation"),
                    "detail": entry.get("detail", ""),
                    "data": entry,
                }
            )

        alert_rows = await storage.list_alert_events(limit=50)
        for alert in alert_rows:
            if ticker and ticker not in (alert.get("detail") or "") and ticker not in (alert.get("title") or ""):
                continue
            events.append(
                {
                    "step": "alert",
                    "at": alert.get("created_at"),
                    "title": alert.get("title", alert.get("event_type", "alert")),
                    "detail": alert.get("detail", ""),
                    "data": alert,
                }
            )

        if approval.get("resolved_at"):
            result = approval.get("execution_result") or {}
            events.append(
                {
                    "step": approval.get("status", "resolved"),
                    "at": approval.get("resolved_at"),
                    "title": f"Approval {approval.get('status')}",
                    "detail": result.get("status") or approval.get("notes", ""),
                    "data": result,
                }
            )

        trades = await storage.list_paper_trades(limit=200)
        linked_trade = next(
            (t for t in trades if t.get("approval_id") == approval_id),
            None,
        )
        if not linked_trade:
            linked_trade = next(
                (
                    t
                    for t in trades
                    if t.get("ticker") == ticker
                    and t.get("side") == approval.get("side")
                    and abs(float(t.get("quantity", 0)) - float(approval.get("quantity", 0))) < 0.01
                ),
                None,
            )
        if linked_trade:
            events.append(
                {
                    "step": "journal_logged",
                    "at": linked_trade.get("created_at"),
                    "title": "Journal entry",
                    "detail": f"{linked_trade.get('status')} · PnL {linked_trade.get('pnl')}",
                    "data": linked_trade,
                }
            )

        events.sort(key=lambda e: _parse_dt(e.get("at")) or datetime.min.replace(tzinfo=timezone.utc))
        return {
            "entry_type": "approval",
            "entry_id": approval_id,
            "approval": approval,
            "proposal": proposals[0] if proposals else None,
            "journal_trade": linked_trade,
            "events": events,
            "event_count": len(events),
        }

    async def replay_trade(self, trade_id: str) -> dict:
        storage = await get_storage()
        trade = await storage.get_paper_trade(trade_id)
        if not trade:
            raise ValueError("Trade not found")

        if trade.get("approval_id"):
            replay = await self.replay_approval(trade["approval_id"])
            replay["entry_type"] = "trade"
            replay["entry_id"] = trade_id
            replay["journal_trade"] = trade
            return replay

        events = [
            {
                "step": "journal_planned",
                "at": trade.get("created_at"),
                "title": f"Paper trade {trade.get('status')}",
                "detail": trade.get("reason") or trade.get("verdict", ""),
                "data": trade,
            }
        ]
        if trade.get("status") == "filled":
            events.append(
                {
                    "step": "filled",
                    "at": trade.get("created_at"),
                    "title": "Trade filled",
                    "detail": f"PnL ${trade.get('pnl', 0)}",
                    "data": trade,
                }
            )

        return {
            "entry_type": "trade",
            "entry_id": trade_id,
            "journal_trade": trade,
            "approval": None,
            "proposal": None,
            "events": events,
            "event_count": len(events),
        }
