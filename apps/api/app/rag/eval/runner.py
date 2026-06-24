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
_DRIFT_BASELINE_KEY = "rag_eval_baseline"
_DRIFT_LAST_KEY = "rag_eval_drift_last"
_FEEDBACK_KEY = "rag_negative_feedback"


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


async def _retrieval_recall(case: dict) -> dict:
    phrases = case.get("must_contain_phrases") or []
    if not phrases:
        return {"skipped": True, "passed": True}

    ticker = (case.get("tickers") or [None])[0]
    hits = await RAGService().search(case["query"], top_k=3, ticker=ticker)
    combined = " ".join(hit.content.lower() for hit in hits)
    missing = [p for p in phrases if p.lower() not in combined]
    return {
        "skipped": False,
        "passed": not missing,
        "missing_phrases": missing,
        "chunk_ids": [hit.id for hit in hits],
    }


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


async def check_rag_drift(report: dict | None = None) -> dict:
    if not settings.rag_drift_check_enabled:
        return {"status": "disabled"}

    report = report or await get_last_eval_report()
    if not report:
        report = await run_rag_eval()

    current_mrr = float(report.get("retrieval_recall_pct", 100.0))
    storage = await get_storage()
    baseline = await storage.get_app_state(_DRIFT_BASELINE_KEY)
    if not baseline:
        await storage.set_app_state(
            _DRIFT_BASELINE_KEY,
            {"mrr": current_mrr, "set_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        )
        result = {
            "status": "ok",
            "drift_detected": False,
            "baseline_set": True,
            "current_mrr": current_mrr,
        }
        await storage.set_app_state(_DRIFT_LAST_KEY, result)
        return result

    baseline_mrr = float(baseline.get("mrr", current_mrr))
    drop = round(baseline_mrr - current_mrr, 1)
    drift_detected = drop > settings.rag_drift_alert_pct
    if not drift_detected and current_mrr > baseline_mrr:
        await storage.set_app_state(
            _DRIFT_BASELINE_KEY,
            {"mrr": current_mrr, "set_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        )

    result = {
        "status": "ok",
        "drift_detected": drift_detected,
        "baseline_mrr": baseline_mrr,
        "current_mrr": current_mrr,
        "drop_pct": drop,
        "alert_threshold_pct": settings.rag_drift_alert_pct,
    }
    await storage.set_app_state(_DRIFT_LAST_KEY, result)
    if drift_detected:
        logger.warning(
            "rag_drift_detected",
            baseline_mrr=baseline_mrr,
            current_mrr=current_mrr,
            drop_pct=drop,
        )
    return result


async def run_rag_drift_check() -> dict:
    return await check_rag_drift()


async def record_negative_rag_feedback(
    *,
    session_id: str,
    rag_chunk_ids: list[str],
    comment: str | None = None,
) -> None:
    if not rag_chunk_ids:
        return
    storage = await get_storage()
    state = await storage.get_app_state(_FEEDBACK_KEY) or {"entries": []}
    entries = list(state.get("entries", []))
    entries.append(
        {
            "session_id": session_id,
            "rag_chunk_ids": rag_chunk_ids,
            "comment": comment,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    await storage.set_app_state(_FEEDBACK_KEY, {"entries": entries[-200:]})


async def run_rag_eval() -> dict:
    """Run golden query router checks, retrieval recall, and ACL leak test."""
    if not settings.rag_eval_enabled:
        return {"status": "disabled"}

    started = time.perf_counter()
    cases = load_golden_queries()
    case_results: list[dict] = []
    tool_hits = 0
    retrieval_hits = 0
    retrieval_cases = 0

    for case in cases:
        tickers = case.get("tickers")
        plan = plan_query(case["query"], tickers=tickers)
        plan_tools = list(dict.fromkeys(plan.rag_tools + plan.direct_calls))
        tool_ok = _tool_selection_score(plan_tools, case)
        freshness_ok = True
        if case.get("freshness"):
            freshness_ok = plan.freshness == case["freshness"]

        retrieval = await _retrieval_recall(case)
        if not retrieval.get("skipped"):
            retrieval_cases += 1
            if retrieval.get("passed"):
                retrieval_hits += 1

        passed = tool_ok and freshness_ok and retrieval.get("passed", True)
        if tool_ok and freshness_ok:
            tool_hits += 1
        case_results.append(
            {
                "id": case.get("id", case["query"][:40]),
                "query": case["query"],
                "passed": passed,
                "plan_tools": plan_tools,
                "freshness": plan.freshness,
                "expected_tools": case.get("expected_tools", []),
                "retrieval": retrieval,
            }
        )

    acl = await _acl_leak_check()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    tool_accuracy = round(tool_hits / len(cases) * 100, 1) if cases else 100.0
    retrieval_recall_pct = (
        round(retrieval_hits / retrieval_cases * 100, 1) if retrieval_cases else 100.0
    )

    report = {
        "status": "ok",
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_ms": elapsed_ms,
        "cases_total": len(cases),
        "cases_passed": sum(1 for c in case_results if c["passed"]),
        "tool_selection_accuracy_pct": tool_accuracy,
        "retrieval_recall_pct": retrieval_recall_pct,
        "acl_leak_rate_pct": 0.0 if acl["passed"] else 100.0,
        "acl_check": acl,
        "infer_rag_smoke": bool(infer_rag_tools("wash sale rule")),
        "cases": case_results,
    }

    storage = await get_storage()
    await storage.set_app_state(_LAST_EVAL_KEY, report)
    drift = await check_rag_drift(report)
    report["drift"] = drift
    logger.info(
        "rag_eval_complete",
        accuracy=tool_accuracy,
        retrieval_recall=retrieval_recall_pct,
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
