"""Reranker provider factory."""

from __future__ import annotations

from app.core.config import settings
from app.providers.reranker.base import RerankerProvider
from app.providers.reranker.mock import MockRerankerProvider

_provider: RerankerProvider | None = None


def get_reranker_provider() -> RerankerProvider | None:
    global _provider
    if not settings.rag_reranker_enabled:
        return None
    if _provider is None:
        _provider = MockRerankerProvider()
    return _provider
