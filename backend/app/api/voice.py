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
from app.voice.stt.gather_stt import GatherSpeechSTT
from app.voice.texml_builder import build_empty_response, build_hangup, build_outbound_answer_texml
from app.integrations.registry import get_voice_webhook_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

_BEEP_WAV = Path(__file__).resolve().parent.parent / "voice" / "static" / "beep.wav"


async def _summarize_conversation(call_log_id: str) -> None:
    db = SessionLocal()
    try:
        await ConversationSummaryService.maybe_summarize(db, call_log_id)
    finally:
        db.close()


def _texml_response(texml: str) -> Response:
    return Response(content=texml, media_type="application/xml")


@router.get("/beep.wav")
def beep_tone() -> FileResponse:
    """Short tone played before speech gather so callers know when to speak."""
    return FileResponse(_BEEP_WAV, media_type="audio/wav")


@router.api_route("/inbound", methods=["GET", "POST"])
async def inbound_call(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Telnyx TeXML webhook when a call comes in. Set as TeXML Application voice URL."""
    params = await get_voice_webhook_adapter().parse_request(request)

    call_sid = params.get("CallSid", "")
    from_number = params.get("From", "")
    to_number = params.get("To", "")

    logger.info("Inbound call", extra={"call_sid": call_sid, "from": from_number, "to": to_number})

    settings = get_settings()
    effective_mode = VoiceModeService.effective_mode()
    if settings.voice_mode == "stream" and effective_mode == "gather":
        logger.info(
            "VOICE_MODE=stream requested; using TeXML gather (Telnyx production path)",
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
            texml = await handle_gather_result(db, existing.id, speech_result, confidence)
            return _texml_response(texml)

    texml = handle_inbound_call(db, call_sid, from_number, to_number)
    return _texml_response(texml)


@router.api_route("/gather", methods=["GET", "POST"])
async def gather_speech(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Telnyx webhook after speech is recognized via <Gather input='speech'>."""
    params = await get_voice_webhook_adapter().parse_request(request)

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

    texml = await handle_gather_result(db, call_log_id, speech_result, confidence)
    return _texml_response(texml)


@router.api_route("/status", methods=["GET", "POST"])
async def call_status(
    request: Request,
    background_tasks: BackgroundTasks,
    call_log_id: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Telnyx call status callback — marks call complete and records duration."""
    params = await get_voice_webhook_adapter().parse_request(request)

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

    return _texml_response(build_empty_response())


@router.get("/mode")
def voice_mode_status() -> dict:
    return VoiceModeService.status()


@router.api_route("/outbound/answer", methods=["GET", "POST"])
async def outbound_answer(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """TeXML for when a customer answers an outbound callback."""
    await get_voice_webhook_adapter().parse_request(request)

    from app.models import Business, CallLog

    call = (
        db.query(CallLog)
        .filter(CallLog.id == call_log_id)
        .first()
    )
    if call is None:
        return _texml_response(build_hangup("Sorry, this call could not be completed."))

    business = db.query(Business).filter(Business.id == call.business_id).first()
    if business is None:
        return _texml_response(build_hangup("Sorry, this call could not be completed."))

    escalation = business.escalation_phone or business.phone_number
    texml = build_outbound_answer_texml(
        business.name,
        escalation,
        reason=call.summary,
    )
    call.status = CallStatus.IN_PROGRESS
    db.commit()
    return _texml_response(texml)


@router.websocket("/stream")
async def media_stream(websocket: WebSocket) -> None:
    """
    Real-time media stream (legacy endpoint).
    Telnyx uses TeXML Gather for speech; stream mode is not implemented for Telnyx.
    """
    await handle_media_stream(websocket)
