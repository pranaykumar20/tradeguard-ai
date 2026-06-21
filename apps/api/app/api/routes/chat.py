"""Chat orchestration — LLM brain with tool routing."""

import json
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.orchestrator import TradeGuardOrchestrator
from app.db.storage import get_storage

router = APIRouter()
orchestrator = TradeGuardOrchestrator()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatFeedbackRequest(BaseModel):
    session_id: str
    message_id: str | None = None
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=500)


class ChatFactor(BaseModel):
    icon: str
    title: str
    detail: str
    severity: str = "medium"


class ChatMetric(BaseModel):
    label: str
    value: str
    highlight: bool = False


class ChatScoreBar(BaseModel):
    label: str
    value: int
    max: int = 100


class ChatHeadline(BaseModel):
    title: str
    source: str = ""
    summary: str = ""
    url: str = ""
    sentiment: float | None = None


class ChatCitation(BaseModel):
    id: int
    kind: str
    label: str
    title: str
    url: str = ""
    snippet: str = ""


class ChatQuote(BaseModel):
    ticker: str
    last_price: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    provider: str | None = None
    live: bool | None = None


class ChatTradePreview(BaseModel):
    ticker: str
    side: str
    quantity: float
    limit_price: float
    order_value: float
    verdict: str


class ChatComparison(BaseModel):
    tickers: list[str]
    rows: list[dict]


class StructuredReply(BaseModel):
    layout: str
    summary: str
    factors: list[ChatFactor] = []
    snapshot: list[ChatMetric] = []
    scores: list[ChatScoreBar] = []
    quote: ChatQuote | None = None
    trade_preview: ChatTradePreview | None = None
    headlines: list[ChatHeadline] = []
    citations: list[ChatCitation] = []
    comparison: ChatComparison | None = None
    disclaimer: str | None = None
    follow_up: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message_id: str | None = None
    reply: str
    narrative: str | None = None
    structured: StructuredReply | None = None
    decision: str
    risk_verdict: str
    warnings: list[str] = []
    suggested_actions: list[str] = []
    trade_preview: dict | None = None
    rag_sources: list[dict] = []
    rag_tools: list[str] = []
    web_sources: list[dict] = []
    quote: dict | None = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await orchestrator.handle_message(
        message=request.message,
        session_id=request.session_id,
    )
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for event in orchestrator.handle_message_stream(
            message=request.message,
            session_id=request.session_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback")
async def chat_feedback(request: ChatFeedbackRequest):
    storage = await get_storage()
    key = f"chat_feedback:{request.session_id}"
    state = await storage.get_app_state(key) or {"entries": []}
    entries = list(state.get("entries", []))
    entries.append(
        {
            "message_id": request.message_id,
            "rating": request.rating,
            "comment": request.comment,
        }
    )
    await storage.set_app_state(key, {"entries": entries[-100:]})
    return {"ok": True, "session_id": request.session_id}
