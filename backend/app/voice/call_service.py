"""Voice call orchestration — ties Telnyx TeXML webhooks to the AI receptionist."""

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ai.receptionist_agent import ReceptionistAgent, get_ai_provider
from app.config import get_settings
from app.models import Business, CallLog
from app.models.enums import CallDirection, CallStatus
from app.services.tenant import is_valid_uuid
from app.domain.call import call_has_booking
from app.domain.phone import normalize_phone
from app.voice.conversation import is_closing_acknowledgment, is_farewell
from app.voice.texml_builder import (
    build_greeting,
    build_hangup,
    build_say_and_gather,
    build_transfer_texml,
)
from app.voice.tts.texml_tts import TeXMLSayTTS

logger = logging.getLogger(__name__)


def find_business_by_phone(db: Session, to_number: str) -> Business | None:
    """Match inbound Telnyx number to a business phone_number."""
    normalized = normalize_phone(to_number)
    businesses = db.query(Business).filter(Business.phone_number.isnot(None)).all()
    for biz in businesses:
        if biz.phone_number and normalize_phone(biz.phone_number) == normalized:
            return biz
    return None


def create_voice_call(
    db: Session,
    business: Business,
    call_sid: str,
    caller_phone: str,
) -> CallLog:
    call = CallLog(
        id=str(uuid4()),
        business_id=business.id,
        external_call_id=call_sid,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
        caller_phone=caller_phone,
        summary="Inbound voice call",
        conversation_history=[],
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    logger.info(
        "Voice call started",
        extra={"call_log_id": call.id, "business_id": business.id, "call_sid": call_sid},
    )
    return call


def get_call_log(db: Session, call_log_id: str, business_id: str | None = None) -> CallLog | None:
    if not is_valid_uuid(call_log_id):
        return None
    query = db.query(CallLog).filter(CallLog.id == call_log_id)
    if business_id:
        query = query.filter(CallLog.business_id == business_id)
    return query.first()


async def process_speech_turn(
    db: Session,
    call_log: CallLog,
    business: Business,
    speech_text: str,
) -> tuple[str, bool]:
    """
    Run one voice conversation turn through the AI receptionist.
    Returns (texml_response, escalated).
    """
    settings = get_settings()
    history: list[dict[str, str]] = list(call_log.conversation_history or [])

    if not settings.groq_api_key:
        return (
            build_hangup("Sorry, our AI receptionist is temporarily unavailable. Please call back later."),
            False,
        )

    if call_has_booking(call_log.summary) and (
        is_farewell(speech_text) or is_closing_acknowledgment(speech_text)
    ):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return (
            build_hangup("You're welcome! Thank you for calling. Goodbye!"),
            False,
        )

    if is_farewell(speech_text):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return (build_hangup("Thank you for calling. Goodbye!"), False)

    call_id = call_log.id
    try:
        agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=call_id)
        result = await agent.chat(speech_text, history, voice_mode=True)
    except Exception:
        db.rollback()
        logger.exception("Voice AI turn failed", extra={"call_log_id": call_id})
        return (
            build_hangup("Sorry, I'm having technical difficulties. Please try again later."),
            False,
        )

    reply = TeXMLSayTTS.prepare_for_speech(result["reply"])
    db.refresh(call_log)
    call_log.escalated = result["escalated"]
    if "book_appointment" in result.get("tools_used", []):
        call_log.summary = "Appointment booked on voice call"
    db.commit()

    if call_has_booking(call_log.summary) and is_farewell(speech_text):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return (build_hangup(f"{reply} Goodbye!"), False)

    if result["escalated"]:
        escalation = business.escalation_phone or business.phone_number
        if escalation:
            return build_transfer_texml(escalation), True
        return (
            build_hangup(
                "I've notified our team about your request. Someone will call you back shortly. Goodbye!"
            ),
            True,
        )

    return build_say_and_gather(reply, settings.public_api_url, call_log.id), False


def handle_inbound_call(db: Session, call_sid: str, from_number: str, to_number: str) -> str:
    """Create call record and return initial TeXML greeting."""
    settings = get_settings()

    existing = (
        db.query(CallLog)
        .filter(
            CallLog.external_call_id == call_sid,
            CallLog.status == CallStatus.IN_PROGRESS,
        )
        .order_by(CallLog.created_at.desc())
        .first()
    )
    if existing:
        logger.info(
            "Resuming in-progress call",
            extra={"call_log_id": existing.id, "call_sid": call_sid},
        )
        return build_say_and_gather(
            "Sorry about that. After the tone, please continue.",
            settings.public_api_url,
            existing.id,
        )

    business = find_business_by_phone(db, to_number)

    if business is None:
        logger.warning("No business for inbound number", extra={"to": to_number})
        return build_hangup("Sorry, this number is not configured. Goodbye.")

    from app.services.subscription_service import SubscriptionService

    denial = SubscriptionService.get_access_denial_reason(business)
    if denial:
        return build_hangup(
            "Sorry, this AI receptionist is currently unavailable. Please visit our website to contact us. Goodbye."
        )

    if not SubscriptionService.is_within_call_limit(db, business):
        return build_hangup(
            "Sorry, we're unable to take your call right now. Please try again later or visit our website. Goodbye."
        )

    call = create_voice_call(db, business, call_sid, from_number)
    return build_greeting(business.name, settings.public_api_url, call.id)


def handle_call_status(
    db: Session,
    call_log_id: str,
    call_status: str,
    call_duration: str | None = None,
) -> None:
    """Update call log when Telnyx sends status callback."""
    call_log = get_call_log(db, call_log_id)
    if call_log is None:
        return

    if call_status in ("completed", "busy", "failed", "no-answer", "canceled"):
        call_log.status = CallStatus.COMPLETED if call_status == "completed" else CallStatus.FAILED
        if call_duration:
            try:
                call_log.duration_seconds = int(call_duration)
            except ValueError:
                pass
        db.commit()
        logger.info(
            "Voice call ended",
            extra={"call_log_id": call_log_id, "status": call_status},
        )
