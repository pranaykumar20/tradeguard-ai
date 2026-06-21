"""Tests for LLM reply validation."""

from app.agents.llm_validator import inject_citation_markers, validate_llm_reply


def test_validate_strips_duplicate_sections():
    raw = """**Don't buy NVDA.**

### Key factors
- ⚠️ **Tech exposure** — too high

### Snapshot
| Metric | Value |
| --- | --- |
| Score | 52 |

Recent news looks mixed."""
    cleaned = validate_llm_reply(raw)
    assert "###" not in cleaned
    assert "|" not in cleaned
    assert "Recent news looks mixed." in cleaned


def test_validate_word_limit():
    raw = " ".join(["word"] * 120)
    cleaned = validate_llm_reply(raw, max_words=90)
    assert cleaned.endswith("…")
    assert len(cleaned.split()) <= 91


def test_inject_citation_markers():
    text = inject_citation_markers("Recent headlines suggest caution.", 2)
    assert "[1]" in text
    assert "[2]" in text
