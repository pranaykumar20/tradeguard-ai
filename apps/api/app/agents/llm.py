"""LLM service — explains analysis; risk engine verdict is always final."""

import asyncio
from pathlib import Path

import structlog

from app.core.config import settings

logger = structlog.get_logger()

_cursor_client = None
_cursor_client_lock = asyncio.Lock()

SYSTEM_PROMPT = """You are TradeGuard AI, a risk-focused stock investing assistant.

Rules you MUST follow:
- The risk engine verdict (ALLOW, CAUTION, or BLOCK) is FINAL — never contradict it.
- If verdict is BLOCK, clearly state the trade is blocked and explain why.
- If verdict is CAUTION, emphasize manual review before any action.
- Phase 1 is analysis-only — no live trades are executed.
- Do not give generic financial advice; ground your reply in the provided context.
- Never recommend options unless explicitly allowed in the context.
- When live web search results are provided, cite recent headlines where relevant.
- When a stock quote is provided in context, state the exact price and change — do not invent prices.

Response format — the UI renders metrics, factors, and tables from structured data. Your markdown reply should add narrative only:

1. One **bold** recommendation sentence (the UI also shows this as the summary).
2. Optional: one short paragraph with context not already in the snapshot (max 2 sentences).
3. One follow-up question on its own line.

Do NOT duplicate tables, bullet lists, or section headers — the UI handles layout.
Keep total reply under 80 words when possible.
When referencing news or playbook sources, use inline citation markers like [1] or [2]."""


def _cursor_workspace() -> str:
    if settings.cursor_workspace:
        return settings.cursor_workspace
    module_dir = Path(__file__).resolve().parent
    for ancestor in module_dir.parents:
        if (ancestor / "apps" / "api").is_dir() and (ancestor / "apps" / "web").is_dir():
            return str(ancestor)
    if len(module_dir.parents) > 2:
        return str(module_dir.parents[2])
    return str(module_dir.parent)


def _cursor_model() -> str:
    model = settings.llm_model.strip()
    if model.startswith("composer"):
        return model
    return "composer-2.5"


async def close_cursor_client() -> None:
    """Shut down the shared Cursor SDK bridge (app shutdown)."""
    global _cursor_client
    async with _cursor_client_lock:
        if _cursor_client is not None:
            await _cursor_client.aclose()
            _cursor_client = None


async def _get_cursor_client():
    """Reuse one SDK bridge process — launching per chat adds ~10s overhead."""
    global _cursor_client
    async with _cursor_client_lock:
        if _cursor_client is None:
            from cursor_sdk import AsyncClient

            _cursor_client = await AsyncClient.launch_bridge(
                workspace=_cursor_workspace(),
                timeout=60,
                client_timeout=120.0,
            )
        return _cursor_client


async def generate_reply(user_message: str, context: str) -> str | None:
    """Return LLM-generated reply, or None if no provider is configured."""
    if settings.llm_provider == "cursor" and settings.cursor_api_key:
        if settings.app_env == "production" and not settings.cursor_cloud_repo_url:
            logger.warning(
                "llm_cursor_skipped",
                reason="CURSOR_CLOUD_REPO_URL required for Composer in production",
            )
            return None
        try:
            return await _cursor_reply(user_message, context)
        except Exception as exc:
            logger.warning("llm_cursor_failed", error=str(exc), model=_cursor_model())
            return None
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        try:
            return await _anthropic_reply(user_message, context)
        except Exception as exc:
            logger.warning("llm_anthropic_failed", error=str(exc))
            return None
    if settings.llm_provider == "openai" and settings.openai_api_key:
        try:
            return await _openai_reply(user_message, context)
        except Exception as exc:
            logger.warning("llm_openai_failed", error=str(exc))
            return None
    # Legacy auto: any configured key when provider not explicitly cursor/openai/anthropic
    if settings.openai_api_key:
        try:
            return await _openai_reply(user_message, context)
        except Exception as exc:
            logger.warning("llm_openai_failed", error=str(exc))
            return None
    return None


async def stream_reply(user_message: str, context: str):
    """Yield narrative tokens. Uses native OpenAI streaming when available."""
    if settings.llm_provider == "openai" and settings.openai_api_key:
        try:
            async for token in _openai_stream(user_message, context):
                yield token
            return
        except Exception as exc:
            logger.warning("llm_openai_stream_failed", error=str(exc))

    if settings.openai_api_key and settings.llm_provider != "anthropic":
        try:
            async for token in _openai_stream(user_message, context):
                yield token
            return
        except Exception as exc:
            logger.warning("llm_openai_stream_failed", error=str(exc))

    reply = await generate_reply(user_message, context)
    if not reply:
        return
    for word in reply.split():
        yield word + " "


async def _openai_stream(user_message: str, context: str):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nUser question:\n{user_message}"},
        ],
        max_tokens=400,
        temperature=0.3,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def _cursor_reply(user_message: str, context: str) -> str:
    from cursor_sdk import AgentOptions, AsyncAgent, CloudAgentOptions, CloudRepository

    options_kwargs: dict = {
        "model": _cursor_model(),
        "api_key": settings.cursor_api_key,
        "mode": "agent",
    }
    if settings.cursor_cloud_repo_url:
        options_kwargs["cloud"] = CloudAgentOptions(
            repos=[CloudRepository(url=settings.cursor_cloud_repo_url)],
        )

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Respond in GitHub-flavored markdown only. Do not edit files, run shell commands, or use tools.\n\n"
        f"Context:\n{context}\n\nUser question:\n{user_message}"
    )

    client = await _get_cursor_client()
    result = await AsyncAgent.prompt(
        prompt,
        AgentOptions(**options_kwargs),
        client=client,
    )
    if result.status == "error":
        raise RuntimeError(f"Cursor agent run failed: {result.id}")
    text = (result.result or "").strip()
    if not text:
        raise RuntimeError("Cursor agent returned empty reply")
    return text


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
