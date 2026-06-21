"""Platform admin — user and permission management."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, require_admin, serialize_user, user_record_to_current
from app.core.permissions import ALL_PERMISSIONS, ROLE_LABELS, effective_permissions
from app.db.storage import get_storage

router = APIRouter()


class UserUpdateBody(BaseModel):
    role: Literal["platform_admin", "trader", "analyst", "viewer", "user"] | None = None
    permissions: list[str] | None = Field(default=None)
    is_active: bool | None = None
    display_name: str | None = None


def _serialize_user_record(record: dict) -> dict:
    current = user_record_to_current(record, is_authenticated=True)
    return {
        **serialize_user(current),
        "custom_permissions": record.get("permissions"),
        "effective_permissions": current.permissions,
        "role_label": ROLE_LABELS.get(current.role, current.role),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


@router.get("/permissions")
async def list_permission_catalog(_admin: CurrentUser = Depends(require_admin)):
    return {
        "permissions": list(ALL_PERMISSIONS),
        "roles": [{"id": k, "label": ROLE_LABELS.get(k, k), "permissions": list(v)} for k, v in {
            "platform_admin": ALL_PERMISSIONS,
            "trader": effective_permissions("trader", None),
            "analyst": effective_permissions("analyst", None),
            "viewer": effective_permissions("viewer", None),
            "user": effective_permissions("user", None),
        }.items()],
    }


@router.get("/users")
async def list_users(_admin: CurrentUser = Depends(require_admin)):
    storage = await get_storage()
    users = await storage.list_users()
    return {"users": [_serialize_user_record(u) for u in users]}


@router.get("/users/{user_id}")
async def get_user(user_id: str, _admin: CurrentUser = Depends(require_admin)):
    storage = await get_storage()
    user = await storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user_record(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateBody,
    admin: CurrentUser = Depends(require_admin),
):
    if user_id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if user_id == admin.id and body.role and body.role != "platform_admin":
        raise HTTPException(status_code=400, detail="Cannot demote your own admin account")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    if body.role is not None and body.permissions is None:
        updates["permissions"] = None

    if body.permissions is not None:
        invalid = [p for p in body.permissions if p not in ALL_PERMISSIONS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid permissions: {invalid}")

    storage = await get_storage()
    updated = await storage.update_user(user_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user_record(updated)
