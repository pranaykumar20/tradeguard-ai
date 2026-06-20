"""Web push subscription and notification inbox API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.push import PushNotificationService

router = APIRouter()
push = PushNotificationService()


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict | None = None
    expirationTime: float | None = None


@router.get("/config")
async def push_config():
    return {
        "enabled": settings.push_notifications_enabled,
        "vapid_public_key": settings.vapid_public_key or None,
    }


@router.post("/subscribe")
async def subscribe(request: PushSubscribeRequest):
    sub = await push.subscribe(request.model_dump())
    return sub


@router.post("/unsubscribe")
async def unsubscribe(request: PushSubscribeRequest):
    return await push.unsubscribe(request.endpoint)


@router.get("/inbox")
async def inbox(limit: int = 20, unread_only: bool = False):
    items = await push.list_inbox(limit=limit, unread_only=unread_only)
    return {"notifications": items, "unread": len([n for n in items if not n.get("read")])}


@router.post("/inbox/{notification_id}/read")
async def mark_read(notification_id: str):
    note = await push.mark_read(notification_id)
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": note}


@router.post("/inbox/read-all")
async def mark_all_read():
    count = await push.mark_all_read()
    return {"marked_read": count}
