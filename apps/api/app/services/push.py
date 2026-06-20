"""Web push & in-app notification inbox — mock-first when VAPID unset."""

from datetime import datetime, timezone
from uuid import uuid4

import structlog

from app.core.config import settings
from app.db.storage import get_storage

logger = structlog.get_logger()


class PushNotificationService:
    async def subscribe(self, subscription: dict) -> dict:
        storage = await get_storage()
        subs = await storage.get_app_state("push_subscriptions") or {"items": []}
        endpoint = subscription.get("endpoint", "")
        items = [s for s in subs.get("items", []) if s.get("endpoint") != endpoint]
        items.append(
            {
                "id": str(uuid4()),
                "endpoint": endpoint,
                "subscription": subscription,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await storage.set_app_state("push_subscriptions", {"items": items})
        return {"status": "subscribed", "count": len(items)}

    async def unsubscribe(self, endpoint: str) -> dict:
        storage = await get_storage()
        subs = await storage.get_app_state("push_subscriptions") or {"items": []}
        items = [s for s in subs.get("items", []) if s.get("endpoint") != endpoint]
        await storage.set_app_state("push_subscriptions", {"items": items})
        return {"status": "unsubscribed", "count": len(items)}

    async def list_subscriptions(self) -> list[dict]:
        storage = await get_storage()
        subs = await storage.get_app_state("push_subscriptions") or {"items": []}
        return subs.get("items", [])

    async def notify(
        self,
        title: str,
        body: str,
        event_type: str,
        severity: str = "medium",
    ) -> dict | None:
        if not settings.push_notifications_enabled:
            return None

        storage = await get_storage()
        inbox = await storage.get_app_state("push_inbox") or {"items": []}
        note = {
            "id": str(uuid4()),
            "title": title,
            "body": body,
            "event_type": event_type,
            "severity": severity,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        items = [note, *inbox.get("items", [])][:100]
        await storage.set_app_state("push_inbox", {"items": items})

        subs = await self.list_subscriptions()
        if subs and settings.vapid_public_key:
            logger.info("push_dispatch", event_type=event_type, subscribers=len(subs))
        else:
            logger.info("push_inbox_only", event_type=event_type, title=title)

        return note

    async def list_inbox(self, limit: int = 20, unread_only: bool = False) -> list[dict]:
        storage = await get_storage()
        inbox = await storage.get_app_state("push_inbox") or {"items": []}
        items = inbox.get("items", [])
        if unread_only:
            items = [n for n in items if not n.get("read")]
        return items[:limit]

    async def mark_read(self, notification_id: str) -> dict | None:
        storage = await get_storage()
        inbox = await storage.get_app_state("push_inbox") or {"items": []}
        updated = None
        for note in inbox.get("items", []):
            if note.get("id") == notification_id:
                note["read"] = True
                updated = note
        if updated:
            await storage.set_app_state("push_inbox", inbox)
        return updated

    async def mark_all_read(self) -> int:
        storage = await get_storage()
        inbox = await storage.get_app_state("push_inbox") or {"items": []}
        count = 0
        for note in inbox.get("items", []):
            if not note.get("read"):
                note["read"] = True
                count += 1
        await storage.set_app_state("push_inbox", inbox)
        return count
