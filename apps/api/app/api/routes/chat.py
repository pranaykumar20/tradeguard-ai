"""Chat orchestration — LLM brain with tool routing."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.orchestrator import TradeGuardOrchestrator

router = APIRouter()
orchestrator = TradeGuardOrchestrator()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    decision: str
    risk_verdict: str
    warnings: list[str] = []
    suggested_actions: list[str] = []
    trade_preview: dict | None = None
    rag_sources: list[dict] = []
    rag_tools: list[str] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await orchestrator.handle_message(
        message=request.message,
        session_id=request.session_id,
    )
    return ChatResponse(**result)
