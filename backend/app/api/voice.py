"""Telnyx TeXML voice webhooks — inbound calls, speech gather, status."""

import logging

from fastapi import APIRouter, Depends, Query, Request, Response, WebSocket
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.voice.call_service import (
    handle_call_status,
    handle_gather_result,
    handle_inbound_call,
)
from app.voice.media_stream_handler import handle_media_stream
from app.voice.texml_builder import build_empty_response, build_hangup
from app.voice.webhook_auth import validate_telnyx_webhook

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


def _texml_response(texml: str) -> Response:
    return Response(content=texml, media_type="application/xml")


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

    texml = handle_inbound_call(db, call_sid, from_number, to_number)
    return _texml_response(texml)


@router.post("/gather")
async def gather_speech(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Telnyx webhook after speech is recognized via <Gather input='speech'>."""
    params = await validate_telnyx_webhook(request)

    speech_result = params.get("SpeechResult")
    confidence = params.get("Confidence")

    logger.info(
        "Speech gathered",
        extra={"call_log_id": call_log_id, "speech": speech_result, "confidence": confidence},
    )

    texml = await handle_gather_result(db, call_log_id, speech_result, confidence)
    return _texml_response(texml)


@router.post("/status")
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
