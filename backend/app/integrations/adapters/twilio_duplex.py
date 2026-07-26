"""Twilio duplex media adapter — Phase 2 bidirectional Media Streams."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.domain.telecom import resolve_voice_locale
from app.voice.duplex.contracts import DuplexMediaAdapter, MediaEvent, MediaStreamBindContext
from app.voice.duplex.media_utils import parse_json_media_message
from app.voice.telnyx_media_stream import is_mp3_audio
from app.voice.twilio_media_stream import (
    build_clear_playback_frame,
    build_outbound_mulaw_frame,
    chunk_mulaw_frames,
)

logger = logging.getLogger(__name__)


class TwilioDuplexMediaAdapter(DuplexMediaAdapter):
    def __init__(self) -> None:
        self._websocket: Any | None = None
        self._bind_context: MediaStreamBindContext | None = None

    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.twilio_account_sid and settings.twilio_auth_token)

    def supports_duplex(self) -> bool:
        return self.is_configured()

    def supports_barge_in(self) -> bool:
        return True

    def supports_websocket_playback(self) -> bool:
        return True

    def preferred_playback_content_type(self) -> str:
        return "audio/mulaw"

    def parse_media_message(self, raw_text: str) -> MediaEvent | None:
        return parse_json_media_message(raw_text, provider_name=self.provider_name)

    def build_session_start_response(
        self,
        *,
        greeting: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        locale = resolve_voice_locale(country)
        url = stream_url.replace("&", "&amp;")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say voice="{locale.voice}" language="{locale.language}">{greeting}</Say>'
            f'<Connect><Stream url="{url}" /></Connect>'
            f'<Pause length="{keep_alive_seconds}"/>'
            "</Response>"
        )

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
            "Twilio duplex WebSocket bound",
            extra={"stream_sid": context.stream_id, "call_sid": context.call_control_id},
        )

    async def unbind_media_websocket(self) -> None:
        self._websocket = None
        self._bind_context = None

    async def stop_playback(self, call_id: str) -> None:
        del call_id
        stream_sid = self._bind_context.stream_id if self._bind_context else None
        if not stream_sid or self._websocket is None:
            return
        try:
            await self._websocket.send_text(build_clear_playback_frame(stream_sid=stream_sid))
        except Exception:
            logger.exception("Twilio duplex clear frame failed", extra={"stream_sid": stream_sid})

    async def deliver_audio(
        self,
        call_id: str,
        audio: bytes,
        *,
        content_type: str = "audio/mulaw",
    ) -> bool:
        del call_id
        stream_sid = self._bind_context.stream_id if self._bind_context else None
        if not stream_sid or not audio or self._websocket is None:
            return False
        if is_mp3_audio(audio, content_type) and content_type not in ("audio/mulaw", "ulaw_8000"):
            logger.warning("Twilio duplex requires mulaw audio — request ulaw_8000 from TTS")
            return False

        try:
            for frame in chunk_mulaw_frames(audio):
                await self._websocket.send_text(
                    build_outbound_mulaw_frame(stream_sid=stream_sid, mulaw_audio=frame)
                )
            return True
        except Exception:
            logger.exception("Twilio duplex outbound audio failed", extra={"stream_sid": stream_sid})
            return False

    async def push_markup(self, call_id: str, markup: str) -> None:
        import asyncio

        from app.voice import twilio_client

        await asyncio.to_thread(twilio_client.update_call_twiml, call_id, markup)

    def build_hangup_response(self, message: str, *, country: str | None = None) -> str:
        from html import escape

        from app.domain.telecom import resolve_voice_locale

        locale = resolve_voice_locale(country)
        text = escape(message, quote=False)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Say voice="{locale.voice}" language="{locale.language}">'
            f"{text}</Say><Hangup/></Response>"
        )

    def build_transfer_response(
        self,
        to_number: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        from html import escape

        from app.domain.telecom import resolve_voice_locale

        locale = resolve_voice_locale(country)
        msg = message or "Please hold while I connect you with a team member."
        text = escape(msg, quote=False)
        phone = escape(to_number.strip(), quote=False)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say voice="{locale.voice}" language="{locale.language}">{text}</Say>'
            f'<Dial timeout="30"><Number>{phone}</Number></Dial>'
            f'<Say voice="{locale.voice}" language="{locale.language}">'
            "Sorry, no one is available right now. We will call you back shortly."
            "</Say><Hangup/></Response>"
        )
