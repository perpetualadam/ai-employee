"""Base duplex adapter — shared TeXML/TwiML-style markup patterns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from html import escape

from app.domain.telecom import resolve_voice_locale
from app.voice.duplex.contracts import DuplexMediaAdapter


class MarkupDuplexAdapter(DuplexMediaAdapter, ABC):
    """Shared markup builders for TeXML and TwiML providers."""

    markup_content_type: str = "application/xml"

    def _say(self, message: str, country: str | None) -> str:
        locale = resolve_voice_locale(country)
        text = escape(message, quote=False)
        return f'<Say voice="{locale.voice}" language="{locale.language}">{text}</Say>'

    def _stream_block(self, stream_url: str, *, codec: str = "PCMU") -> str:
        url = escape(stream_url, quote=True)
        return (
            "<Start>"
            f'<Stream url="{url}" track="inbound_track" codec="{codec}" />'
            "</Start>"
        )

    def build_session_start_response(
        self,
        *,
        greeting: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        return self._wrap_response(
            f"{self._say(greeting, country)}"
            f"{self._stream_block(stream_url)}"
            f"<Pause length=\"{keep_alive_seconds}\"/>",
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

    async def stop_playback(self, call_id: str) -> None:
        del call_id

    async def deliver_audio(self, call_id: str, audio: bytes, *, content_type: str = "audio/mulaw") -> bool:
        del call_id, audio, content_type
        return False

    async def push_markup(self, call_id: str, markup: str) -> None:
        await self._push_call_markup(call_id, markup)

    @abstractmethod
    async def _push_call_markup(self, call_id: str, markup: str) -> None:
        ...

    @abstractmethod
    def _wrap_response(self, inner: str) -> str:
        ...
