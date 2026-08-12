"""Telnyx TeXML voice webhooks — inbound calls, speech gather, status."""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, WebSocket
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models.enums import CallStatus
from app.services.conversation_summary_service import ConversationSummaryService
from app.voice.call_service import handle_call_status, handle_inbound_call
from app.voice.gather_handler import handle_gather_result
from app.services.voice_mode_service import VoiceModeService
from app.voice.media_stream_handler import handle_media_stream
from app.voice.duplex.handler import handle_duplex_stream
from app.voice.stt.gather_stt import GatherSpeechSTT
from app.voice.voice_markup import get_voice_markup, resolve_voice_markup
from app.integrations.registry import get_voice_webhook_adapter_for_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

_BEEP_WAV = Path(__file__).resolve().parent.parent / "voice" / "static" / "beep.wav"


async def _summarize_conversation(call_log_id: str) -> None:
    db = SessionLocal()
    try:
        await ConversationSummaryService.maybe_summarize(db, call_log_id)
    finally:
        db.close()


def _markup_response(markup: str, content_type: str) -> Response:
    return Response(content=markup, media_type=content_type)


@router.get("/beep.wav")
def beep_tone() -> FileResponse:
    """Short tone played before speech gather so callers know when to speak."""
    return FileResponse(_BEEP_WAV, media_type="audio/wav")


@router.get("/plivo/xml")
def plivo_pushed_xml(call_uuid: str = Query(...)) -> Response:
    """Serve stashed PlivoXML for live call transfers (Plivo aleg_url)."""
    from app.voice import plivo_client

    xml = plivo_client.pop_call_xml(call_uuid) or plivo_client.peek_call_xml(call_uuid)
    if not xml:
        xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
    return Response(content=xml, media_type="application/xml")


@router.api_route("/inbound", methods=["GET", "POST"])
async def inbound_call(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """CPaaS voice webhook when a call comes in."""
    webhook = get_voice_webhook_adapter_for_request(request)
    markup_builder = get_voice_markup(webhook.provider_name)
    params = await webhook.parse_request(request)

    call_sid = params.get("CallSid", "")
    from_number = params.get("From", "")
    to_number = params.get("To", "")

    logger.info("Inbound call", extra={"call_sid": call_sid, "from": from_number, "to": to_number})

    settings = get_settings()
    effective_mode = VoiceModeService.effective_mode()
    if settings.voice_mode == "stream" and effective_mode == "gather":
        logger.info(
            "VOICE_MODE=stream requested; using TeXML gather (streaming not fully configured)",
            extra={"requested": settings.voice_mode, "effective": effective_mode},
        )
    if settings.voice_mode == "duplex" and effective_mode == "gather":
        logger.info(
            "VOICE_MODE=duplex requested; using TeXML gather (duplex not fully configured)",
            extra={"requested": settings.voice_mode, "effective": effective_mode},
        )

    # Telnyx may POST speech to inbound if the gather action URL failed (e.g. 500).
    speech_result, confidence = GatherSpeechSTT.extract_from_params(params)
    if not GatherSpeechSTT.is_empty(speech_result) and call_sid:
        from app.models import CallLog
        from app.models.enums import CallStatus

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
                "Recovering speech via inbound fallback",
                extra={"call_log_id": existing.id, "speech": speech_result},
            )
            markup = await handle_gather_result(db, existing.id, speech_result, confidence)
            return _markup_response(markup, markup_builder.content_type)

    markup = handle_inbound_call(db, call_sid, from_number, to_number)
    return _markup_response(markup, markup_builder.content_type)


@router.api_route("/gather", methods=["GET", "POST"])
async def gather_speech(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """CPaaS webhook after speech is recognized."""
    webhook = get_voice_webhook_adapter_for_request(request)
    markup_builder = get_voice_markup(webhook.provider_name)
    params = await webhook.parse_request(request)

    speech_result, confidence = GatherSpeechSTT.extract_from_params(params)

    if GatherSpeechSTT.is_empty(speech_result):
        logger.warning(
            "Empty gather result",
            extra={"call_log_id": call_log_id, "params": params},
        )
    else:
        logger.info(
            "Speech gathered",
            extra={"call_log_id": call_log_id, "speech": speech_result, "confidence": confidence},
        )

    markup = await handle_gather_result(db, call_log_id, speech_result, confidence)
    return _markup_response(markup, markup_builder.content_type)


@router.api_route("/status", methods=["GET", "POST"])
async def call_status(
    request: Request,
    background_tasks: BackgroundTasks,
    call_log_id: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Call status callback — marks call complete and records duration."""
    webhook = get_voice_webhook_adapter_for_request(request)
    markup_builder = get_voice_markup(webhook.provider_name)
    params = await webhook.parse_request(request)

    if call_log_id:
        status_value = params.get("CallStatus", "")
        handle_call_status(
            db,
            call_log_id,
            status_value,
            params.get("CallDuration"),
        )
        if status_value == "completed":
            background_tasks.add_task(_summarize_conversation, call_log_id)

    return _markup_response(markup_builder.build_empty(), markup_builder.content_type)


@router.api_route("/recording-status", methods=["GET", "POST"])
async def recording_status(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Provider recordingStatusCallback — download and store call audio for owner review."""
    webhook = get_voice_webhook_adapter_for_request(request)
    markup_builder = get_voice_markup(webhook.provider_name)
    params = await webhook.parse_request(request)

    from app.services.call_recording_service import CallRecordingService

    CallRecordingService.handle_recording_status(
        db,
        call_log_id=call_log_id,
        params=params,
        provider=webhook.provider_name,
    )
    return _markup_response(markup_builder.build_empty(), markup_builder.content_type)


@router.get("/mode")
def voice_mode_status() -> dict:
    return VoiceModeService.status()


@router.api_route("/outbound/answer", methods=["GET", "POST"])
async def outbound_answer(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Voice markup when a customer answers an outbound callback."""
    webhook = get_voice_webhook_adapter_for_request(request)
    await webhook.parse_request(request)

    from app.models import Business, CallLog

    call = (
        db.query(CallLog)
        .filter(CallLog.id == call_log_id)
        .first()
    )
    markup_builder = get_voice_markup(call.provider if call and call.provider else webhook.provider_name)
    if call is None:
        return _markup_response(
            markup_builder.build_hangup("Sorry, this call could not be completed."),
            markup_builder.content_type,
        )

    business = db.query(Business).filter(Business.id == call.business_id).first()
    if business is None:
        return _markup_response(
            markup_builder.build_hangup("Sorry, this call could not be completed."),
            markup_builder.content_type,
        )

    escalation = business.escalation_phone or business.phone_number
    markup = markup_builder.build_outbound_answer(
        business.name,
        escalation,
        reason=call.summary,
        country=business.country,
    )
    call.status = CallStatus.IN_PROGRESS
    db.commit()
    return _markup_response(markup, markup_builder.content_type)


@router.websocket("/duplex/stream")
async def duplex_media_stream(
    websocket: WebSocket,
    call_log_id: str = Query(...),
    call_sid: str = Query(default=""),
) -> None:
    """Persistent CPaaS media stream — duplex STT + barge-in (Telnyx, Twilio, Vonage)."""
    await handle_duplex_stream(
        websocket,
        call_log_id=call_log_id,
        call_sid=call_sid or None,
    )


@router.websocket("/stream")
async def media_stream(
    websocket: WebSocket,
    call_log_id: str = Query(...),
    call_sid: str = Query(default=""),
) -> None:
    """Telnyx TeXML media stream — Deepgram live STT when VOICE_MODE=stream."""
    await handle_media_stream(
        websocket,
        call_log_id=call_log_id,
        call_sid=call_sid or None,
    )
