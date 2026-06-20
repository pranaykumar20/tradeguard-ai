"""Regulatory-style audit exports — 90-day journal, approvals, automation log."""

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.storage import get_storage


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _in_window(value: str | None, cutoff: datetime) -> bool:
    dt = _parse_dt(value)
    if not dt:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


class AuditExportService:
    async def collect(self, days: int | None = None) -> dict:
        days = min(days or settings.audit_export_max_days, settings.audit_export_max_days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        storage = await get_storage()

        trades = [
            t
            for t in await storage.list_paper_trades(limit=1000)
            if _in_window(t.get("created_at"), cutoff)
        ]
        approvals = [
            a
            for a in await storage.list_approval_requests(status=None, limit=1000)
            if _in_window(a.get("created_at"), cutoff)
        ]
        audit = [
            e
            for e in await storage.list_automation_audit(limit=1000)
            if _in_window(e.get("created_at"), cutoff)
        ]
        alerts = [
            e
            for e in await storage.list_alert_events(limit=500)
            if _in_window(e.get("created_at"), cutoff)
        ]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "counts": {
                "journal_trades": len(trades),
                "approval_requests": len(approvals),
                "automation_audit": len(audit),
                "alert_events": len(alerts),
            },
            "journal_trades": trades,
            "approval_requests": approvals,
            "automation_audit": audit,
            "alert_events": alerts,
        }

    async def export_json(self, days: int | None = None) -> str:
        payload = await self.collect(days=days)
        return json.dumps(payload, indent=2, default=str)

    async def export_csv(self, days: int | None = None) -> str:
        payload = await self.collect(days=days)
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["section", "id", "created_at", "summary", "status", "detail"])
        for trade in payload["journal_trades"]:
            writer.writerow(
                [
                    "journal",
                    trade.get("id"),
                    trade.get("created_at"),
                    f"{trade.get('side')} {trade.get('quantity')} {trade.get('ticker')}",
                    trade.get("status"),
                    trade.get("reason", "")[:200],
                ]
            )
        for approval in payload["approval_requests"]:
            writer.writerow(
                [
                    "approval",
                    approval.get("id"),
                    approval.get("created_at"),
                    f"{approval.get('side')} {approval.get('quantity')} {approval.get('ticker')}",
                    approval.get("status"),
                    (approval.get("notes") or "")[:200],
                ]
            )
        for entry in payload["automation_audit"]:
            writer.writerow(
                [
                    "automation",
                    entry.get("id"),
                    entry.get("created_at"),
                    entry.get("event_type"),
                    entry.get("verdict"),
                    (entry.get("detail") or "")[:200],
                ]
            )
        for alert in payload["alert_events"]:
            writer.writerow(
                [
                    "alert",
                    alert.get("id"),
                    alert.get("created_at"),
                    alert.get("title"),
                    alert.get("severity"),
                    (alert.get("detail") or "")[:200],
                ]
            )
        return buffer.getvalue()
