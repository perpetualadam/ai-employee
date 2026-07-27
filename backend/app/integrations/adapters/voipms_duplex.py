"""VoIP.ms duplex adapter — SIP carrier; duplex media streams not supported."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.voice.duplex.contracts import DuplexMediaAdapter, MediaEvent, MediaStreamBindContext


class VoipMsDuplexMediaAdapter(DuplexMediaAdapter):
    @property
    def provider_name(self) -> str:
        return "voipms"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.voipms_api_username and settings.voipms_api_password)

    def supports_duplex(self) -> bool:
        return False

    def supports_barge_in(self) -> bool:
        return False

    def supports_websocket_playback(self) -> bool:
        return False

    def preferred_playback_content_type(self) -> str:
        return "audio/l16"

    def parse_media_message(self, raw_text: str) -> MediaEvent | None:
        del raw_text
        return None

    def build_session_start_response(
        self,
        *,
        greeting: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        del greeting, stream_url, country, keep_alive_seconds
        return "ok"

    def build_reply_response(
        self,
        *,
        message: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        del message, stream_url, country, keep_alive_seconds
        return "ok"

    async def bind_media_websocket(
        self,
        websocket: Any,
        *,
        context: MediaStreamBindContext,
    ) -> None:
        del websocket, context

    async def unbind_media_websocket(self) -> None:
        return None

    async def push_markup(self, call_id: str, markup: str) -> None:
        del call_id, markup

    async def stop_playback(self, call_control_id: str | None = None) -> None:
        del call_control_id

    async def deliver_audio(self, audio: bytes, *, content_type: str = "audio/l16") -> None:
        del audio, content_type

    def build_hangup_response(self, message: str, *, country: str | None = None) -> str:
        del message, country
        return "ok"

    def build_transfer_response(
        self,
        to_number: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        del to_number, message, country
        return "ok"
