"""Telnyx TeXML voice webhooks — inbound calls, speech gather, status."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, Response, WebSocket
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.voice.call_service import handle_call_status, handle_inbound_call
from app.voice.gather_handler import handle_gather_result
from app.voice.media_stream_handler import handle_media_stream
from app.voice.stt.gather_stt import GatherSpeechSTT
from app.voice.texml_builder import build_empty_response, build_hangup
from app.voice.webhook_auth import validate_telnyx_webhook

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

_BEEP_WAV = Path(__file__).resolve().parent.parent / "voice" / "static" / "beep.wav"


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
    params = await validate_telnyx_webhook(request)

    call_sid = params.get("CallSid", "")
    from_number = params.get("From", "")
    to_number = params.get("To", "")

    logger.info("Inbound call", extra={"call_sid": call_sid, "from": from_number, "to": to_number})

    settings = get_settings()
    if settings.voice_mode == "stream":
        logger.warning(
            "VOICE_MODE=stream is not supported with Telnyx; using gather mode. "
            "Set VOICE_MODE=gather in .env."
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
    params = await validate_telnyx_webhook(request)

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
    call_log_id: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Telnyx call status callback — marks call complete and records duration."""
    params = await validate_telnyx_webhook(request)

    if call_log_id:
        handle_call_status(
            db,
            call_log_id,
            params.get("CallStatus", ""),
            params.get("CallDuration"),
        )

    return _texml_response(build_empty_response())


@router.websocket("/stream")
async def media_stream(websocket: WebSocket) -> None:
    """
    Real-time media stream (legacy endpoint).
    Telnyx uses TeXML Gather for speech; stream mode is not implemented for Telnyx.
    """
    await handle_media_stream(websocket)
