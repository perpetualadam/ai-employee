"""Provider-agnostic duplex voice contracts — Telnyx, Twilio, Vonage, and future CPaaS."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


class MediaEventType(str, enum.Enum):
    START = "start"
    MEDIA = "media"
    STOP = "stop"
    MARK = "mark"


@dataclass(frozen=True)
class MediaEvent:
    """Normalized media stream event from any CPaaS provider."""

    event_type: MediaEventType
    audio_payload: bytes | None = None
    call_id: str | None = None
    stream_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class MediaStreamBindContext:
    """Context captured from a CPaaS media stream START frame."""

    call_control_id: str | None = None
    stream_id: str | None = None
    media_encoding: str = "PCMU"
    bidirectional_mode: str = "mp3"


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    is_final: bool
    confidence: float | None = None


class DuplexMediaAdapter(ABC):
    """Parse provider media WebSockets and deliver replies without vendor names in core."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def supports_duplex(self) -> bool:
        ...

    @abstractmethod
    def supports_barge_in(self) -> bool:
        ...

    def supports_websocket_playback(self) -> bool:
        """True when outbound audio can be sent on the media WebSocket."""
        return False

    async def bind_media_websocket(
        self,
        websocket: Any,
        *,
        context: MediaStreamBindContext,
    ) -> None:
        """Attach the live media WebSocket for bidirectional playback (Phase 2)."""
        del websocket, context

    async def unbind_media_websocket(self) -> None:
        """Release the bound media WebSocket."""

    def uses_binary_media(self) -> bool:
        """True when inbound caller audio arrives as binary WebSocket frames."""
        return False

    def parse_binary_media(self, payload: bytes) -> MediaEvent | None:
        """Convert a binary media frame to a normalized MediaEvent."""
        del payload
        return None

    def preferred_playback_content_type(self) -> str:
        """MIME type TTS should target for this provider's outbound playback."""
        return "audio/mulaw"

    def stt_audio_encoding(self) -> tuple[str, int]:
        """Deepgram live-stream encoding and sample rate for inbound caller audio."""
        return ("mulaw", 8000)

    @abstractmethod
    def parse_media_message(self, raw_text: str) -> MediaEvent | None:
        """Convert provider JSON/text frame to a normalized MediaEvent."""

    @abstractmethod
    def build_session_start_response(
        self,
        *,
        greeting: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        """Return TeXML/TwiML/NCCO to start a persistent media session."""

    @abstractmethod
    def build_reply_response(
        self,
        *,
        message: str,
        stream_url: str,
        country: str | None = None,
        keep_alive_seconds: int = 3600,
    ) -> str:
        """Push assistant speech and re-attach inbound media stream for the next turn."""

    @abstractmethod
    async def stop_playback(self, call_id: str) -> None:
        """Interrupt assistant audio when caller barges in."""

    @abstractmethod
    async def deliver_audio(
        self,
        call_id: str,
        audio: bytes,
        *,
        content_type: str = "audio/mulaw",
    ) -> bool:
        """Stream synthesized speech to the caller. Returns True when audio was delivered."""

    @abstractmethod
    async def push_markup(self, call_id: str, markup: str) -> None:
        """Push provider markup (TeXML/TwiML/NCCO) mid-call."""

    def build_hangup_response(self, message: str, *, country: str | None = None) -> str:
        from app.voice.texml_builder import build_hangup

        return build_hangup(message, country=country)

    def build_transfer_response(
        self,
        to_number: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        from app.voice.texml_builder import build_transfer_texml

        return build_transfer_texml(to_number, message, country=country)
