"""Vonage duplex media adapter — Phase 2 binary L16 WebSocket playback."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.voice.duplex.contracts import DuplexMediaAdapter, MediaEvent, MediaStreamBindContext
from app.voice.duplex.vonage_media_utils import (
    parse_vonage_binary_media,
    parse_vonage_text_message,
)
from app.voice.vonage_media_stream import build_clear_command, chunk_l16_frames

logger = logging.getLogger(__name__)

_VONAGE_L16_RATE = 16000


class VonageDuplexMediaAdapter(DuplexMediaAdapter):
    def __init__(self) -> None:
        self._websocket: Any | None = None
        self._bind_context: MediaStreamBindContext | None = None

    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.vonage_api_key and settings.vonage_api_secret)

    def supports_duplex(self) -> bool:
        return self.is_configured()

    def supports_barge_in(self) -> bool:
        return True

    def supports_websocket_playback(self) -> bool:
        return True

    def uses_binary_media(self) -> bool:
        return True

    def preferred_playback_content_type(self) -> str:
        return "audio/l16"

    def stt_audio_encoding(self) -> tuple[str, int]:
        return ("linear16", _VONAGE_L16_RATE)

    def parse_media_message(self, raw_text: str) -> MediaEvent | None:
        return parse_vonage_text_message(raw_text)

    def parse_binary_media(self, payload: bytes) -> MediaEvent | None:
        return parse_vonage_binary_media(payload)

    def build_session_start_response(
        self,
        *,
        greeting: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        del country, keep_alive_seconds
        ncco = [
            {"action": "talk", "text": greeting},
            {
                "action": "connect",
                "endpoint": [
                    {
                        "type": "websocket",
                        "uri": stream_url,
                        "content-type": f"audio/l16;rate={_VONAGE_L16_RATE}",
                    }
                ],
            },
        ]
        return json.dumps(ncco)

    def build_reply_response(
        self,
        *,
        message: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        return self.build_session_start_response(
            greeting=message,
            stream_url=stream_url,
            country=country,
            keep_alive_seconds=keep_alive_seconds,
        )

    async def bind_media_websocket(
        self,
        websocket: Any,
        *,
        context: MediaStreamBindContext,
    ) -> None:
        self._websocket = websocket
        self._bind_context = context
        logger.info(
            "Vonage duplex WebSocket bound",
            extra={"call_uuid": context.call_control_id},
        )

    async def unbind_media_websocket(self) -> None:
        self._websocket = None
        self._bind_context = None

    async def stop_playback(self, call_id: str) -> None:
        del call_id
        if self._websocket is None:
            return
        try:
            await self._websocket.send_text(build_clear_command())
        except Exception:
            logger.exception("Vonage duplex clear command failed")

    async def deliver_audio(
        self,
        call_id: str,
        audio: bytes,
        *,
        content_type: str = "audio/mulaw",
    ) -> bool:
        del call_id, content_type
        if not audio or self._websocket is None:
            return False
        try:
            for frame in chunk_l16_frames(audio, sample_rate=_VONAGE_L16_RATE):
                await self._websocket.send_bytes(frame)
            return True
        except Exception:
            logger.exception("Vonage duplex outbound audio failed")
            return False

    async def push_markup(self, call_id: str, markup: str) -> None:
        import asyncio

        from app.voice import vonage_client

        call_uuid = (self._bind_context.call_control_id if self._bind_context else None) or call_id
        await asyncio.to_thread(vonage_client.update_call_ncco, call_uuid, markup)

    def build_hangup_response(self, message: str, *, country: str | None = None) -> str:
        del country
        return json.dumps(
            [
                {"action": "talk", "text": message},
                {"action": "hangup"},
            ]
        )

    def build_transfer_response(
        self,
        to_number: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        del country
        msg = message or "Please hold while I connect you with a team member."
        return json.dumps(
            [
                {"action": "talk", "text": msg},
                {
                    "action": "connect",
                    "endpoint": [{"type": "phone", "number": to_number.strip()}],
                },
            ]
        )
