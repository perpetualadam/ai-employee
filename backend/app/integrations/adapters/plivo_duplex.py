"""Plivo duplex media adapter — Stream XML + WebSocket frames."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.domain.telecom import resolve_voice_locale
from app.voice.duplex.contracts import DuplexMediaAdapter, MediaEvent, MediaStreamBindContext
from app.voice.duplex.media_utils import parse_json_media_message

logger = logging.getLogger(__name__)


class PlivoDuplexMediaAdapter(DuplexMediaAdapter):
    def __init__(self) -> None:
        self._websocket: Any | None = None
        self._bind_context: MediaStreamBindContext | None = None

    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.plivo_auth_id and settings.plivo_auth_token)

    def supports_duplex(self) -> bool:
        return self.is_configured()

    def supports_barge_in(self) -> bool:
        return True

    def supports_websocket_playback(self) -> bool:
        return True

    def preferred_playback_content_type(self) -> str:
        return "audio/l16"

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
            f'<Speak language="{locale.language}">{greeting}</Speak>'
            f'<Stream streamTimeout="{keep_alive_seconds}" keepCallAlive="true" '
            f'contentType="audio/x-l16;rate=16000" bidirection="true">{url}</Stream>'
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

    async def unbind_media_websocket(self) -> None:
        self._websocket = None
        self._bind_context = None

    async def push_markup(self, call_id: str, markup: str) -> None:
        from app.voice import plivo_client

        plivo_client.update_call_xml(call_id, markup)

    async def stop_playback(self, call_control_id: str | None = None) -> None:
        del call_control_id

    async def deliver_audio(self, audio: bytes, *, content_type: str = "audio/l16") -> None:
        del audio, content_type

    def build_hangup_response(self, message: str, *, country: str | None = None) -> str:
        from app.voice.voice_markup import PlivoVoiceMarkup

        return PlivoVoiceMarkup().build_hangup(message, country=country)

    def build_transfer_response(
        self,
        to_number: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        from app.voice.voice_markup import PlivoVoiceMarkup

        return PlivoVoiceMarkup().build_transfer(to_number, message, country=country)
