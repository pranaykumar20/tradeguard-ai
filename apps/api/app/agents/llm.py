"""LLM service — explains analysis; risk engine verdict is always final."""

from pathlib import Path

import structlog

from app.core.config import settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are TradeGuard AI, a risk-focused stock investing assistant.

Rules you MUST follow:
- The risk engine verdict (ALLOW, CAUTION, or BLOCK) is FINAL — never contradict it.
- If verdict is BLOCK, clearly state the trade is blocked and explain why.
- If verdict is CAUTION, emphasize manual review before any action.
- Phase 1 is analysis-only — no live trades are executed.
- Be concise, use markdown headers and bullet points.
- Do not give generic financial advice; ground your reply in the provided context.
- Never recommend options unless explicitly allowed in the context."""


def _cursor_workspace() -> str:
    if settings.cursor_workspace:
        return settings.cursor_workspace
    # apps/api/app/agents/llm.py -> monorepo root
    return str(Path(__file__).resolve().parents[4])


def _cursor_model() -> str:
    model = settings.llm_model.strip()
    if model.startswith("composer"):
        return model
    return "composer-2.5"


async def generate_reply(user_message: str, context: str) -> str | None:
    """Return LLM-generated reply, or None if no provider is configured."""
    if settings.llm_provider == "cursor" and settings.cursor_api_key:
        return await _cursor_reply(user_message, context)
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return await _anthropic_reply(user_message, context)
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return await _openai_reply(user_message, context)
    # Legacy auto: any configured key when provider not explicitly cursor/openai/anthropic
    if settings.openai_api_key:
        return await _openai_reply(user_message, context)
    return None


async def _cursor_reply(user_message: str, context: str) -> str:
    from cursor_sdk import AgentOptions, AsyncAgent, CloudAgentOptions, CloudRepository, LocalAgentOptions

    options_kwargs: dict = {
        "model": _cursor_model(),
        "api_key": settings.cursor_api_key,
        "mode": "plan",
    }
    if settings.cursor_cloud_repo_url:
        options_kwargs["cloud"] = CloudAgentOptions(
            repos=[CloudRepository(url=settings.cursor_cloud_repo_url)],
        )
    else:
        options_kwargs["local"] = LocalAgentOptions(cwd=_cursor_workspace())

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Respond in markdown only. Do not edit files, run shell commands, or use tools.\n\n"
        f"Context:\n{context}\n\nUser question:\n{user_message}"
    )

    try:
        result = await AsyncAgent.prompt(prompt, AgentOptions(**options_kwargs))
        if result.status == "error":
            raise RuntimeError(f"Cursor agent run failed: {result.id}")
        text = (result.result or "").strip()
        if not text:
            raise RuntimeError("Cursor agent returned empty reply")
        return text
    except Exception as exc:
        logger.warning("llm_cursor_failed", error=str(exc), model=_cursor_model())
        raise


async def _openai_reply(user_message: str, context: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nUser question:\n{user_message}",
                },
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("llm_openai_failed", error=str(exc))
        raise


async def _anthropic_reply(user_message: str, context: str) -> str:
    import httpx

    model = settings.llm_model if "claude" in settings.llm_model else "claude-3-5-haiku-20241022"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 800,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Context:\n{context}\n\nUser question:\n{user_message}",
                        }
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    except Exception as exc:
        logger.warning("llm_anthropic_failed", error=str(exc))
        raise
