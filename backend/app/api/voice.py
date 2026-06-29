"""Twilio voice webhooks — inbound calls, speech gather, status, media stream."""

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
from app.voice.twiml_builder import build_empty_response, build_hangup, build_media_stream_connect
from app.voice.webhook_auth import validate_twilio_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


def _twiml_response(twiml: str) -> Response:
    return Response(content=twiml, media_type="application/xml")


@router.post("/inbound")
async def inbound_call(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Twilio webhook when a call comes in. Configure as Voice URL on your Twilio number."""
    params = await validate_twilio_signature(request)

    call_sid = params.get("CallSid", "")
    from_number = params.get("From", "")
    to_number = params.get("To", "")

    logger.info("Inbound call", extra={"call_sid": call_sid, "from": from_number, "to": to_number})

    settings = get_settings()

    # Media stream mode when Deepgram is configured
    if settings.voice_mode == "stream" and settings.deepgram_api_key:
        from app.voice.call_service import create_voice_call, find_business_by_phone

        business = find_business_by_phone(db, to_number)
        if business is None:
            return _twiml_response(build_hangup("Sorry, this number is not configured. Goodbye."))

        call = create_voice_call(db, business, call_sid, from_number)
        ws_url = settings.public_api_url.replace("https://", "wss://").replace("http://", "ws://")
        stream_url = f"{ws_url.rstrip('/')}/api/v1/voice/stream"
        twiml = build_media_stream_connect(stream_url, call.id)
        return _twiml_response(twiml)

    twiml = handle_inbound_call(db, call_sid, from_number, to_number)
    return _twiml_response(twiml)


@router.post("/gather")
async def gather_speech(
    request: Request,
    call_log_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Twilio webhook after speech is recognized via <Gather input='speech'>."""
    params = await validate_twilio_signature(request)

    speech_result = params.get("SpeechResult")
    confidence = params.get("Confidence")

    logger.info(
        "Speech gathered",
        extra={"call_log_id": call_log_id, "speech": speech_result, "confidence": confidence},
    )

    twiml = await handle_gather_result(db, call_log_id, speech_result, confidence)
    return _twiml_response(twiml)


@router.post("/status")
async def call_status(
    request: Request,
    call_log_id: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Twilio call status callback — marks call complete and records duration."""
    params = await validate_twilio_signature(request)

    if call_log_id:
        handle_call_status(
            db,
            call_log_id,
            params.get("CallStatus", ""),
            params.get("CallDuration"),
        )

    return _twiml_response(build_empty_response())


@router.websocket("/stream")
async def media_stream(websocket: WebSocket) -> None:
    """
    Twilio Media Streams WebSocket for real-time audio.
    Used when VOICE_MODE=stream and DEEPGRAM_API_KEY is set.
    """
    await handle_media_stream(websocket)
