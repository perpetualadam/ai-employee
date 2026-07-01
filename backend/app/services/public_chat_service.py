"""Customer-facing public web chat — standalone and voice continuation."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.receptionist_agent import ReceptionistAgent, create_text_session, get_ai_provider
from app.config import get_settings
from app.models import Business, CallLog
from app.models.enums import CallStatus
from app.services.business_slug_service import BusinessSlugService
from app.services.conversation_summary_service import ConversationSummaryService
from app.services.subscription_service import SubscriptionService
from app.services.web_continuation_service import WebContinuationService

logger = logging.getLogger(__name__)


class PublicChatService:
    @staticmethod
    def get_business_for_slug(db: Session, slug: str) -> Business:
        business = BusinessSlugService.resolve_by_slug(db, slug)
        if business is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
        PublicChatService._assert_chat_available(db, business)
        if not business.public_slug:
            BusinessSlugService.ensure_unique_slug(db, business)
        return business

    @staticmethod
    def get_session_for_continue_token(db: Session, token: str) -> tuple[Business, CallLog]:
        record = WebContinuationService.resolve_token(db, token)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This link is invalid or has expired.",
            )

        business = db.query(Business).filter(Business.id == record.business_id).first()
        call = (
            db.query(CallLog)
            .filter(CallLog.id == record.call_log_id, CallLog.business_id == record.business_id)
            .first()
        )
        if business is None or call is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        PublicChatService._assert_chat_available(db, business)
        return business, call

    @staticmethod
    def _assert_chat_available(db: Session, business: Business) -> None:
        reason = SubscriptionService.get_access_denial_reason(business)
        if reason:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=reason)
        if not SubscriptionService.is_within_call_limit(db, business):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This business is temporarily unavailable. Please call back later.",
            )

    @staticmethod
    async def chat(
        db: Session,
        business: Business,
        *,
        user_message: str,
        history: list[dict[str, str]],
        session_id: str | None = None,
        customer_phone: str | None = None,
        existing_call: CallLog | None = None,
    ) -> dict:
        settings = get_settings()
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI receptionist is temporarily unavailable.",
            )

        if existing_call is not None:
            call = existing_call
            session_id = call.id
        elif session_id:
            call = (
                db.query(CallLog)
                .filter(CallLog.id == session_id, CallLog.business_id == business.id)
                .first()
            )
            if call is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        else:
            phone = (customer_phone or "").strip() or "web-chat"
            call = create_text_session(db, business.id, caller_phone=phone)
            session_id = call.id

        if call.status == CallStatus.COMPLETED and not existing_call:
            call.status = CallStatus.IN_PROGRESS
            db.commit()

        try:
            agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=session_id)
            result = await agent.chat(user_message, history, voice_mode=False)
        except Exception:
            logger.exception("Public chat failed", extra={"business_id": business.id})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI receptionist error. Please try again.",
            ) from None

        await ConversationSummaryService.maybe_summarize(db, session_id)

        return {
            "reply": result["reply"],
            "session_id": session_id,
            "tools_used": result["tools_used"],
            "escalated": result["escalated"],
            "owner_notified": result.get("owner_notified", False),
        }
