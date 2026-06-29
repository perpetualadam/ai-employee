"""Media stream WebSocket handler — not used with Telnyx TeXML gather mode."""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def handle_media_stream(websocket: WebSocket) -> None:
    """
    Telnyx voice uses TeXML Gather for speech recognition (VOICE_MODE=gather).
    Real-time media streaming is not implemented for Telnyx in this app.
    """
    await websocket.accept()
    logger.warning("Media stream connection rejected — use VOICE_MODE=gather with Telnyx")
    await websocket.close(code=1008, reason="Media stream not supported; use TeXML gather mode")
