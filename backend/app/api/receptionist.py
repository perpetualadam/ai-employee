"""AI receptionist chat endpoints."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.receptionist_agent import (
    ReceptionistAgent,
    create_text_session,
    get_ai_provider,
)
from app.config import get_settings
from app.core.deps import require_active_subscription
from app.core.rate_limit import limiter
from app.database import SessionLocal, get_db
from app.models import Business, CallLog
from app.schemas import ChatRequest, ChatResponse
from app.services.conversation_summary_service import ConversationSummaryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/receptionist", tags=["receptionist"])


async def _summarize_conversation(call_log_id: str) -> None:
    db = SessionLocal()
    try:
        await ConversationSummaryService.maybe_summarize(db, call_log_id)
    finally:
        db.close()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_with_receptionist(
    request: Request,
    data: ChatRequest,
    background_tasks: BackgroundTasks,
    business: Business = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> ChatResponse:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI receptionist is not configured. Set GROQ_API_KEY in environment.",
        )

    session_id = data.session_id
    if session_id:
        call = (
            db.query(CallLog)
            .filter(CallLog.id == session_id, CallLog.business_id == business.id)
            .first()
        )
        if call is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    else:
        call = create_text_session(db, business.id, data.caller_phone)
        session_id = call.id

    try:
        provider = get_ai_provider()
        agent = ReceptionistAgent(db, business, provider, call_log_id=session_id)
        result = await agent.chat(
            user_message=data.message,
            history=[h.model_dump() for h in data.history],
        )
    except Exception as exc:
        logger.exception("Receptionist chat failed", extra={"business_id": business.id})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI receptionist error: {exc}",
        ) from exc

    background_tasks.add_task(_summarize_conversation, session_id)

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        tools_used=result["tools_used"],
        escalated=result["escalated"],
        owner_notified=result.get("owner_notified", False),
    )
