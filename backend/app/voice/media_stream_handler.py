"""Media stream WebSocket handler — future Call Control streaming path."""

import logging

from fastapi import WebSocket

from app.services.voice_mode_service import VoiceModeService

logger = logging.getLogger(__name__)


async def handle_media_stream(websocket: WebSocket) -> None:
    """
    Real-time media streaming endpoint (reserved for Call Control + Deepgram).
    Telnyx production voice uses TeXML Gather — see VoiceModeService.status().
    """
    await websocket.accept()
    mode = VoiceModeService.status()
    reason = (
        "Media stream is not active. "
        f"Effective voice mode: {mode['effective_mode']}. "
        f"{mode['note']}"
    )
    logger.info("Media stream connection closed", extra={"voice_mode": mode})
    await websocket.close(code=1008, reason=reason[:120])
