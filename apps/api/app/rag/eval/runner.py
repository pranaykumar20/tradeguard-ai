"""RAG evaluation — golden query suite and metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path

import structlog

from app.core.config import settings
from app.core.user_context import user_scope
from app.db.storage import _rag_visible_to_user, get_storage
from app.rag.router import plan_query
from app.rag.service import RAGService
from app.rag.tool_routing import infer_rag_tools

logger = structlog.get_logger()

_GOLDEN_PATH = Path(__file__).resolve().parent / "golden_queries.json"
_LAST_EVAL_KEY = "rag_eval_last"


def load_golden_queries() -> list[dict]:
    if not _GOLDEN_PATH.is_file():
        return []
    return json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))


def _tool_selection_score(plan_tools: list[str], case: dict) -> bool:
    expected = case.get("expected_tools") or []
    if not expected:
        return True
    combined = set(plan_tools)
    if not all(tool in combined for tool in expected):
        return False
    forbidden = case.get("forbidden_tools") or []
    return not any(tool in combined for tool in forbidden)


async def _acl_leak_check() -> dict:
    storage = await get_storage()
    leak_detected = False
    async with user_scope("eval-user-a"):
        await storage.upsert_rag_documents(
            [
                {
                    "chunk_id": "eval-journal-a-only",
                    "source": "Trade journal — NVDA buy",
                    "content": "Secret journal entry for user A only.",
                    "embedding": [0.1] * settings.embedding_dimensions,
                    "meta": {
                        "type": "journal",
                        "user_id": "eval-user-a",
                        "visibility": "user",
                    },
                }
            ]
        )
    async with user_scope("eval-user-b"):
        hits = await RAGService().search(
            "Secret journal entry user A",
            top_k=5,
            doc_types=["journal"],
        )
        leak_detected = any("eval-journal-a-only" == h.id for h in hits)
    return {"passed": not leak_detected, "leak_detected": leak_detected}


async def run_rag_eval() -> dict:
    """Run golden query router checks and ACL leak test."""
    if not settings.rag_eval_enabled:
        return {"status": "disabled"}

    started = time.perf_counter()
    cases = load_golden_queries()
    case_results: list[dict] = []
    tool_hits = 0

    for case in cases:
        tickers = case.get("tickers")
        plan = plan_query(case["query"], tickers=tickers)
        plan_tools = list(dict.fromkeys(plan.rag_tools + plan.direct_calls))
        tool_ok = _tool_selection_score(plan_tools, case)
        freshness_ok = True
        if case.get("freshness"):
            freshness_ok = plan.freshness == case["freshness"]
        passed = tool_ok and freshness_ok
        if passed:
            tool_hits += 1
        case_results.append(
            {
                "id": case.get("id", case["query"][:40]),
                "query": case["query"],
                "passed": passed,
                "plan_tools": plan_tools,
                "freshness": plan.freshness,
                "expected_tools": case.get("expected_tools", []),
            }
        )

    acl = await _acl_leak_check()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    tool_accuracy = round(tool_hits / len(cases) * 100, 1) if cases else 100.0

    report = {
        "status": "ok",
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_ms": elapsed_ms,
        "cases_total": len(cases),
        "cases_passed": tool_hits,
        "tool_selection_accuracy_pct": tool_accuracy,
        "acl_leak_rate_pct": 0.0 if acl["passed"] else 100.0,
        "acl_check": acl,
        "infer_rag_smoke": bool(infer_rag_tools("wash sale rule")),
        "cases": case_results,
    }

    storage = await get_storage()
    await storage.set_app_state(_LAST_EVAL_KEY, report)
    logger.info(
        "rag_eval_complete",
        accuracy=tool_accuracy,
        acl_passed=acl["passed"],
        elapsed_ms=elapsed_ms,
    )
    return report


async def get_last_eval_report() -> dict | None:
    storage = await get_storage()
    return await storage.get_app_state(_LAST_EVAL_KEY)


def visibility_allows(meta: dict | None, user_id: str) -> bool:
    """Public helper mirroring storage ACL — used in tests."""
    return _rag_visible_to_user(meta, user_id)
