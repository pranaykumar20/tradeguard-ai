"""Phase 5 P3 — eval, ACL, citation grounding, migration."""

import pytest

from app.agents.llm_validator import (
    validate_authority_compliance,
    validate_citation_markers,
    validate_grounded_reply,
)
from app.db.storage import _rag_visible_to_user
from app.rag.eval.runner import _tool_selection_score, load_golden_queries, visibility_allows


def test_visibility_acl_user_scoped():
    assert visibility_allows({"visibility": "global"}, "user-a") is True
    assert visibility_allows({"visibility": "user", "user_id": "user-a"}, "user-a") is True
    assert visibility_allows({"visibility": "user", "user_id": "user-a"}, "user-b") is False
    assert _rag_visible_to_user({"type": "journal", "user_id": "a", "visibility": "user"}, "a")
    assert not _rag_visible_to_user({"type": "journal", "user_id": "a", "visibility": "user"}, "b")


def test_validate_citation_markers():
    ok = validate_citation_markers("See [1] and [2] for details.", max_citation_id=3)
    assert ok["valid"] is True
    bad = validate_citation_markers("See [9] for details.", max_citation_id=3)
    assert bad["valid"] is False


def test_validate_authority_compliance_block():
    bad = validate_authority_compliance("It is safe to buy NVDA now.", "BLOCK")
    assert bad["compliant"] is False
    good = validate_authority_compliance("This trade is blocked due to concentration.", "BLOCK")
    assert good["compliant"] is True


def test_validate_grounded_reply_combined():
    result = validate_grounded_reply(
        "Blocked — do not proceed. [1]",
        risk_verdict="BLOCK",
        citation_count=2,
    )
    assert result["grounded"] is True


def test_tool_selection_score():
    assert _tool_selection_score(["search_filings", "get_quote"], {"expected_tools": ["search_filings"]})
    assert not _tool_selection_score(
        ["search_playbooks"],
        {"expected_tools": ["get_quote"], "forbidden_tools": ["search_playbooks"]},
    )


def test_golden_queries_load():
    cases = load_golden_queries()
    assert len(cases) >= 5
    assert any(c["id"] == "wash-sale-playbook" for c in cases)


@pytest.mark.asyncio
async def test_run_rag_eval():
    from app.rag.eval.runner import run_rag_eval

    report = await run_rag_eval()
    assert report["status"] == "ok"
    assert report["cases_total"] >= 5
    assert report["acl_check"]["passed"] is True
