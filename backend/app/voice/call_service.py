"""Voice call orchestration — ties Telnyx TeXML webhooks to the AI receptionist."""

import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ai.receptionist_agent import ReceptionistAgent, get_ai_provider
from app.config import get_settings
from app.models import Business, CallLog
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.services.tenant import is_valid_uuid
from app.domain.call import call_has_booking
from app.domain.phone import normalize_phone
from app.voice.conversation import is_closing_acknowledgment, is_farewell
from app.voice.voice_markup import get_voice_markup, resolve_voice_markup
from app.voice.tts.texml_tts import TeXMLSayTTS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DuplexTurnResult:
    reply: str
    action: str = "continue"  # continue | hangup | transfer
    transfer_to: str | None = None


def find_business_by_phone(db: Session, to_number: str) -> Business | None:
    """Match inbound Telnyx number to a tenant business phone_number."""
    normalized = normalize_phone(to_number)
    if not normalized:
        return None

    for biz in db.query(Business).filter(Business.phone_number.isnot(None)).all():
        if biz.phone_number and normalize_phone(biz.phone_number, biz.country) == normalized:
            return biz

    # Single-tenant dev fallback: env Telnyx number maps to the only business.
    settings = get_settings()
    env_number = (
        normalize_phone(settings.telnyx_phone_number) if settings.telnyx_phone_number else None
    )
    if env_number and env_number == normalized:
        businesses = db.query(Business).all()
        if len(businesses) == 1:
            return businesses[0]

    return None


def create_voice_call(
    db: Session,
    business: Business,
    call_sid: str,
    caller_phone: str,
) -> CallLog:
    from app.providers.factory import get_telephony_provider

    telephony = get_telephony_provider(business=business, db=db)
    call = CallLog(
        id=str(uuid4()),
        business_id=business.id,
        external_call_id=call_sid,
        provider=telephony.provider_name,
        channel=ConversationChannel.VOICE,
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
    from app.plugins.publishers import publish_call_started

    publish_call_started(
        business_id=business.id,
        call_log_id=call.id,
        caller_phone=caller_phone,
        provider=telephony.provider_name,
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
    Returns (voice_markup_response, escalated).
    """
    settings = get_settings()
    country = business.country
    markup = get_voice_markup(call_log.provider or "telnyx")
    history: list[dict[str, str]] = list(call_log.conversation_history or [])

    if not settings.groq_api_key:
        return (
            markup.build_hangup(
                "Sorry, our AI receptionist is temporarily unavailable. Please call back later.",
                country=country,
            ),
            False,
        )

    if call_has_booking(call_log.summary) and (
        is_farewell(speech_text) or is_closing_acknowledgment(speech_text)
    ):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return (
            markup.build_hangup("You're welcome! Thank you for calling. Goodbye!", country=country),
            False,
        )

    if is_farewell(speech_text):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return (markup.build_hangup("Thank you for calling. Goodbye!", country=country), False)

    call_id = call_log.id
    try:
        agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=call_id)
        result = await agent.chat(speech_text, history, voice_mode=True)
    except Exception:
        db.rollback()
        logger.exception("Voice AI turn failed", extra={"call_log_id": call_id})
        return (
            markup.build_hangup(
                "Sorry, I'm having technical difficulties. Please try again later.",
                country=country,
            ),
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
        return (markup.build_hangup(f"{reply} Goodbye!", country=country), False)

    if result["escalated"]:
        escalation = business.escalation_phone or business.phone_number
        if escalation:
            return markup.build_transfer(escalation, country=country), True
        return (
            markup.build_hangup(
                "I've notified our team about your request. Someone will call you back shortly. Goodbye!",
                country=country,
            ),
            True,
        )

    return (
        markup.build_say_and_gather(
            reply,
            settings.public_api_url,
            call_log.id,
            call_sid=call_log.external_call_id,
            country=country,
        ),
        False,
    )


async def process_duplex_turn(
    db: Session,
    call_log: CallLog,
    business: Business,
    speech_text: str,
) -> DuplexTurnResult:
    """Run one duplex conversation turn — returns reply text and call action, not TeXML."""
    settings = get_settings()
    country = business.country
    history: list[dict[str, str]] = list(call_log.conversation_history or [])

    if not settings.groq_api_key:
        return DuplexTurnResult(
            reply="Sorry, our AI receptionist is temporarily unavailable. Please call back later.",
            action="hangup",
        )

    if call_has_booking(call_log.summary) and (
        is_farewell(speech_text) or is_closing_acknowledgment(speech_text)
    ):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return DuplexTurnResult(reply="You're welcome! Thank you for calling. Goodbye!", action="hangup")

    if is_farewell(speech_text):
        call_log.status = CallStatus.COMPLETED
        db.commit()
        return DuplexTurnResult(reply="Thank you for calling. Goodbye!", action="hangup")

    call_id = call_log.id
    try:
        agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=call_id)
        result = await agent.chat(speech_text, history, voice_mode=True)
    except Exception:
        db.rollback()
        logger.exception("Duplex AI turn failed", extra={"call_log_id": call_id})
        return DuplexTurnResult(
            reply="Sorry, I'm having technical difficulties. Please try again later.",
            action="hangup",
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
        return DuplexTurnResult(reply=f"{reply} Goodbye!", action="hangup")

    if result["escalated"]:
        escalation = business.escalation_phone or business.phone_number
        if escalation:
            return DuplexTurnResult(reply=reply, action="transfer", transfer_to=escalation)
        return DuplexTurnResult(
            reply="I've notified our team about your request. Someone will call you back shortly. Goodbye!",
            action="hangup",
        )

    return DuplexTurnResult(reply=reply, action="continue")


def handle_inbound_call(db: Session, call_sid: str, from_number: str, to_number: str) -> str:
    """Create call record and return initial voice markup greeting."""
    settings = get_settings()
    default_markup = resolve_voice_markup()

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
        resume_business = db.query(Business).filter(Business.id == existing.business_id).first()
        resume_country = resume_business.country if resume_business else None
        resume_markup = get_voice_markup(existing.provider or default_markup.provider_name)
        return resume_markup.build_say_and_gather(
            "Sorry about that. After the tone, please continue.",
            settings.public_api_url,
            existing.id,
            call_sid=call_sid,
            country=resume_country,
        )

    business = find_business_by_phone(db, to_number)

    if business is None:
        logger.warning("No business for inbound number", extra={"to": to_number})
        return default_markup.build_hangup("Sorry, this number is not configured. Goodbye.")

    business_markup = resolve_voice_markup(business=business, db=db)

    from app.services.subscription_service import SubscriptionService

    denial = SubscriptionService.get_access_denial_reason(business)
    if denial:
        return business_markup.build_hangup(
            "Sorry, this AI receptionist is currently unavailable. Please visit our website to contact us. Goodbye.",
            country=business.country,
        )

    if not SubscriptionService.is_within_call_limit(db, business):
        return business_markup.build_hangup(
            "Sorry, we're unable to take your call right now. Please try again later or visit our website. Goodbye.",
            country=business.country,
        )

    call = create_voice_call(db, business, call_sid, from_number)
    markup = business_markup.build_greeting(
        business, settings.public_api_url, call.id, call_sid=call_sid
    )
    if getattr(business, "recording_enabled", False):
        from app.integrations.registry import get_call_recording_adapter
        from app.services.call_recording_service import CallRecordingService
        from app.voice.recording_markup import with_call_recording

        provider_name = business_markup.provider_name
        adapter = get_call_recording_adapter(provider_name)
        if adapter.supports_inline_recording():
            updated = with_call_recording(
                markup,
                base_url=settings.public_api_url,
                call_log_id=call.id,
                provider=provider_name,
                enabled=True,
            )
            if updated != markup:
                markup = updated
                CallRecordingService.mark_recording_started(db, call)
    return markup


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
        from app.plugins.publishers import publish_call_ended

        publish_call_ended(
            business_id=call_log.business_id,
            call_log_id=call_log_id,
            status=call_status,
            duration_seconds=call_log.duration_seconds,
        )
