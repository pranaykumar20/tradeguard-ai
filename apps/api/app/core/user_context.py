"""Request-scoped user id for multi-tenant storage queries."""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncIterator, Awaitable, Callable, TypeVar

from app.core.auth import DEFAULT_USER_ID

T = TypeVar("T")

_current_user_id: ContextVar[str] = ContextVar("current_user_id", default=DEFAULT_USER_ID)


def get_current_user_id() -> str:
    return _current_user_id.get()


def set_current_user_id(user_id: str):
    return _current_user_id.set(user_id)


def reset_current_user_id(token) -> None:
    _current_user_id.reset(token)


@asynccontextmanager
async def user_scope(user_id: str) -> AsyncIterator[None]:
    token = set_current_user_id(user_id)
    try:
        yield
    finally:
        reset_current_user_id(token)


async def for_each_user(fn: Callable[[], Awaitable[T]]) -> list[T]:
    """Run an async callable under each known user id (background jobs)."""
    from app.db.storage import get_storage

    storage = await get_storage()
    user_ids = await storage.list_user_ids()
    results: list[T] = []
    for user_id in user_ids:
        async with user_scope(user_id):
            results.append(await fn())
    return results
