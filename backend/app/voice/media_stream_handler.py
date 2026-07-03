"""Media stream WebSocket handler — Telnyx TeXML Stream + Deepgram STT."""

import logging

from fastapi import WebSocket

from app.services.voice_mode_service import VoiceModeService
from app.voice.voice_stream_service import process_telnyx_media_stream

logger = logging.getLogger(__name__)


async def handle_media_stream(
    websocket: WebSocket,
    *,
    call_log_id: str,
    call_sid: str | None,
) -> None:
    """Delegate Telnyx stream connections to Deepgram-backed transcription."""
    if not VoiceModeService.streaming_available():
        mode = VoiceModeService.status()
        reason = (
            "Media stream unavailable. "
            f"Effective mode: {mode['effective_mode']}. "
            "Set DEEPGRAM_API_KEY, TELNYX_ACCOUNT_SID, and VOICE_MODE=stream."
        )
        logger.info("Media stream rejected", extra={"call_log_id": call_log_id, "mode": mode})
        await websocket.accept()
        await websocket.close(code=1008, reason=reason[:120])
        return

    await process_telnyx_media_stream(
        websocket,
        call_log_id=call_log_id,
        call_sid=call_sid,
    )
