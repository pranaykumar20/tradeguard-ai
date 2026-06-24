"""LRU caches for RAG query embeddings and search results."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import asdict
from typing import Any

from app.core.config import settings

_embedding_cache: OrderedDict[str, tuple[list[float], float]] = OrderedDict()
_result_cache: OrderedDict[str, tuple[list[dict], float]] = OrderedDict()
_cache_generation = 0


def _now() -> float:
    return time.monotonic()


def _ttl() -> float:
    return float(settings.rag_query_cache_ttl_seconds)


def _cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def invalidate_rag_caches() -> None:
    global _cache_generation
    _cache_generation += 1
    _embedding_cache.clear()
    _result_cache.clear()


def get_cached_embedding(key: str) -> list[float] | None:
    if not settings.rag_query_cache_enabled:
        return None
    entry = _embedding_cache.get(key)
    if not entry:
        return None
    vector, expires = entry
    if expires < _now():
        _embedding_cache.pop(key, None)
        return None
    _embedding_cache.move_to_end(key)
    return vector


def set_cached_embedding(key: str, vector: list[float]) -> None:
    if not settings.rag_query_cache_enabled:
        return
    _embedding_cache[key] = (vector, _now() + _ttl())
    _embedding_cache.move_to_end(key)
    while len(_embedding_cache) > settings.rag_query_cache_max_entries:
        _embedding_cache.popitem(last=False)


def get_cached_results(key: str) -> list[dict] | None:
    if not settings.rag_query_cache_enabled:
        return None
    entry = _result_cache.get(key)
    if not entry:
        return None
    rows, expires = entry
    if expires < _now():
        _result_cache.pop(key, None)
        return None
    _result_cache.move_to_end(key)
    return rows


def set_cached_results(key: str, rows: list[Any]) -> None:
    if not settings.rag_query_cache_enabled:
        return
    serialized = [
        asdict(row) if hasattr(row, "__dataclass_fields__") else dict(row)
        for row in rows
    ]
    _result_cache[key] = (serialized, _now() + _ttl())
    _result_cache.move_to_end(key)
    while len(_result_cache) > settings.rag_query_cache_max_entries:
        _result_cache.popitem(last=False)


def embedding_cache_key(query: str, *, generation: int | None = None) -> str:
    gen = generation if generation is not None else _cache_generation
    return _cache_key("embed", gen, query)


def result_cache_key(
    query: str,
    *,
    top_k: int,
    ticker: str | None,
    doc_types: list[str] | None,
    generation: int | None = None,
) -> str:
    gen = generation if generation is not None else _cache_generation
    return _cache_key("result", gen, query, top_k, ticker, doc_types or [])
