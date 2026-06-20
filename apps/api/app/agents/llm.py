"""LLM service — explains analysis; risk engine verdict is always final."""

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


async def generate_reply(user_message: str, context: str) -> str | None:
    """Return LLM-generated reply, or None if no provider is configured."""
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return await _anthropic_reply(user_message, context)
    if settings.openai_api_key:
        return await _openai_reply(user_message, context)
    return None


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
