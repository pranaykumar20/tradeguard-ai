"""Phase 3 RAG retrieval — hybrid search, query rewrite, rerank, recency."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import settings

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "and",
        "but",
        "if",
        "or",
        "because",
        "until",
        "while",
        "of",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "it",
        "they",
        "them",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "am",
        "about",
        "buy",
        "sell",
        "should",
        "today",
        "more",
    }
)

PLAYBOOK_HINTS = (
    "limit order",
    "market order",
    "position size",
    "circuit breaker",
    "vix",
    "exposure",
    "sector",
    "options",
    "wash sale",
    "daily loss",
    "concentration",
    "playbook",
    "rule",
    "guardrail",
)

FILING_HINTS = (
    "10-k",
    "10k",
    "10-q",
    "sec",
    "filing",
    "risk factor",
    "md&a",
    "fundamental",
    "annual report",
    "edgar",
)

NEWS_HINTS = (
    "news",
    "headline",
    "sentiment",
    "earnings",
    "announcement",
    "reported",
    "today",
)

QUERY_EXPANSIONS: dict[str, str] = {
    "vix": "VIX volatility index rising high-volatility regime",
    "wash sale": "wash sale tax lot 30 day window loss disallowed",
    "concentration": "single-name concentration sector exposure limit",
    "options": "options manual approval blocked policy",
    "circuit breaker": "daily loss circuit breaker halt trading",
    "tech exposure": "technology sector exposure limit diversification",
    "limit order": "limit order volatile ticker no market orders",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


def rewrite_query(query: str, ticker: str | None = None) -> str:
    if not settings.rag_query_rewrite_enabled:
        base = query
    else:
        q = query.lower()
        extras: list[str] = []
        for term, expansion in QUERY_EXPANSIONS.items():
            if term in q:
                extras.append(expansion)
        base = query if not extras else f"{query} {' '.join(extras)}"

    if ticker:
        return f"{ticker} risk factors sector exposure concentration {base}"
    return base


def infer_doc_types(query: str) -> list[str] | None:
    """Return doc types to search, or None for all types."""
    if not settings.rag_type_routing_enabled:
        return None

    q = query.lower()
    types: list[str] = []
    if any(hint in q for hint in PLAYBOOK_HINTS):
        types.append("playbook")
    if any(hint in q for hint in FILING_HINTS):
        types.append("filing")
    if any(hint in q for hint in NEWS_HINTS):
        types.append("news")

    if not types:
        return None
    return list(dict.fromkeys(types))


def keyword_score(query: str, content: str) -> float:
    query_terms = tokenize(query)
    if not query_terms:
        return 0.0

    content_lower = content.lower()
    score = 0.0
    for term in query_terms:
        if term in content_lower:
            tf = content_lower.count(term)
            score += 1.0 + math.log1p(tf)

    q_lower = query.lower().strip()
    if len(q_lower) > 4 and q_lower in content_lower:
        score += 3.0

    for term, expansion in QUERY_EXPANSIONS.items():
        if term in q_lower and term in content_lower:
            score += 1.5

    return score


def reciprocal_rank_fusion(rank_lists: list[list[str]], k: int | None = None) -> dict[str, float]:
    k = k or settings.rag_rrf_k
    scores: dict[str, float] = {}
    for ranked_ids in rank_lists:
        for rank, doc_id in enumerate(ranked_ids):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def recency_multiplier(meta: dict | None, half_life_days: int | None = None) -> float:
    if not settings.rag_recency_decay_enabled:
        return 1.0

    meta = meta or {}
    doc_type = meta.get("type")
    if doc_type == "playbook":
        return 1.0

    half_life_by_type = {
        "news": 7,
        "filing": 180,
        "journal": 365,
        "analysis_snapshot": 30,
        "ml_run": 90,
    }
    if doc_type not in half_life_by_type:
        return 1.0

    half_life = half_life_days or half_life_by_type.get(
        doc_type, settings.rag_recency_half_life_days
    )
    date_str = (
        meta.get("published_at")
        or meta.get("filed_at")
        or meta.get("closed_at")
        or meta.get("as_of")
        or meta.get("trained_at")
    )
    parsed = _parse_date(date_str)
    if not parsed:
        return 1.0

    age_days = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400)
    if age_days <= 1:
        return 1.25
    return max(0.75, math.pow(0.5, age_days / half_life))


_TEMPORAL_RULES: list[tuple[re.Pattern[str], timedelta | None]] = [
    (re.compile(r"\blast\s+week\b", re.I), timedelta(days=7)),
    (re.compile(r"\blast\s+month\b", re.I), timedelta(days=30)),
    (re.compile(r"\blast\s+quarter\b", re.I), timedelta(days=90)),
    (re.compile(r"\blast\s+year\b", re.I), timedelta(days=365)),
    (re.compile(r"\blast\s+(\d+)\s+days?\b", re.I), None),
]


def parse_temporal_window(query: str) -> tuple[datetime, datetime] | None:
    if not settings.rag_temporal_filter_enabled:
        return None

    now = datetime.now(timezone.utc)
    for pattern, delta in _TEMPORAL_RULES:
        match = pattern.search(query)
        if not match:
            continue
        if delta is None:
            days = int(match.group(1))
            return now - timedelta(days=days), now
        return now - delta, now
    return None


def _doc_timestamp(meta: dict | None) -> datetime | None:
    meta = meta or {}
    for key in ("as_of", "published_at", "closed_at", "filed_at", "trained_at"):
        parsed = _parse_date(meta.get(key))
        if parsed:
            return parsed
    return None


def apply_temporal_filter(documents: list[dict], query: str) -> list[dict]:
    window = parse_temporal_window(query)
    if not window:
        return documents

    start, end = window
    filtered = []
    for doc in documents:
        ts = _doc_timestamp(doc.get("meta"))
        if ts and start <= ts <= end:
            filtered.append(doc)
    return filtered if filtered else documents


@dataclass
class ScoredDocument:
    chunk_id: str
    content: str
    source: str
    meta: dict | None
    vector_score: float
    keyword_score: float
    hybrid_score: float
    final_score: float


def _matches_doc_types(meta: dict | None, doc_types: list[str] | None) -> bool:
    if not doc_types:
        return True
    doc_type = (meta or {}).get("type", "document")
    return doc_type in doc_types


def rerank_candidates(
    query: str,
    candidates: list[dict],
    *,
    hybrid_scores: dict[str, float],
    preferred_types: list[str] | None,
    top_k: int,
) -> list[ScoredDocument]:
    scored: list[ScoredDocument] = []
    for doc in candidates:
        chunk_id = doc.get("chunk_id") or doc.get("id", "")
        content = doc.get("content", "")
        meta = doc.get("meta") or {}
        kw = keyword_score(query, content)
        hybrid = hybrid_scores.get(chunk_id, float(doc.get("score", 0)))

        type_boost = 1.0
        if preferred_types and meta.get("type") in preferred_types:
            type_boost = 1.15

        recency = recency_multiplier(meta)
        overlap = kw / max(1.0, len(tokenize(query)))
        final = (hybrid * 0.55 + min(overlap, 3.0) * 0.25 + min(kw, 6.0) * 0.05) * recency * type_boost

        scored.append(
            ScoredDocument(
                chunk_id=chunk_id,
                content=content,
                source=doc.get("source", ""),
                meta=meta,
                vector_score=float(doc.get("score", 0)),
                keyword_score=kw,
                hybrid_score=hybrid,
                final_score=final,
            )
        )

    scored.sort(key=lambda item: item.final_score, reverse=True)
    return scored[:top_k]


def hybrid_merge(
    query: str,
    vector_ranked: list[dict],
    keyword_ranked: list[dict],
) -> dict[str, float]:
    if not settings.rag_hybrid_search_enabled:
        return {
            (doc.get("chunk_id") or doc.get("id", "")): float(doc.get("score", 0))
            for doc in vector_ranked
        }

    vector_ids = [doc.get("chunk_id") or doc.get("id", "") for doc in vector_ranked]
    keyword_ids = [doc.get("chunk_id") or doc.get("id", "") for doc in keyword_ranked]
    return reciprocal_rank_fusion([vector_ids, keyword_ids])
