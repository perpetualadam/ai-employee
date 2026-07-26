"""Voice mode resolution — gather (TeXML) vs stream vs duplex."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings
from app.dependencies.plugins import get_speech_to_text_plugin
from app.integrations.registry import get_duplex_media_adapter
from app.voice.voice_markup import resolve_voice_markup

if TYPE_CHECKING:
    from app.models import Business
    from sqlalchemy.orm import Session


class VoiceModeService:
    @staticmethod
    def effective_mode() -> str:
        """
        Return the voice mode actually used for inbound calls.
        Falls back to gather when stream/duplex prerequisites are missing.
        """
        settings = get_settings()
        requested = (settings.voice_mode or "gather").lower()
        if requested == "duplex" and not VoiceModeService.duplex_available():
            return "gather"
        if requested == "stream" and not VoiceModeService.streaming_available():
            return "gather"
        return requested

    @staticmethod
    def streaming_available(
        *,
        business: Business | None = None,
        db: Session | None = None,
    ) -> bool:
        stt = get_speech_to_text_plugin()
        if stt is None or not stt.is_configured():
            return False
        markup = resolve_voice_markup(business=business, db=db)
        return markup.supports_streaming() and markup.is_configured()

    @staticmethod
    def duplex_available(
        *,
        business: Business | None = None,
        db: Session | None = None,
    ) -> bool:
        stt = get_speech_to_text_plugin()
        if stt is None or not stt.is_configured():
            return False
        try:
            adapter = get_duplex_media_adapter(business=business, db=db)
        except KeyError:
            return False
        return adapter.is_configured() and adapter.supports_duplex()

    @staticmethod
    def status() -> dict:
        settings = get_settings()
        stt = get_speech_to_text_plugin()
        duplex_adapter = None
        try:
            duplex_adapter = get_duplex_media_adapter()
        except KeyError:
            pass
        return {
            "requested_mode": settings.voice_mode,
            "effective_mode": VoiceModeService.effective_mode(),
            "streaming_available": VoiceModeService.streaming_available(),
            "duplex_available": VoiceModeService.duplex_available(),
            "duplex_provider": duplex_adapter.provider_name if duplex_adapter else None,
            "production_recommendation": "gather",
            "speech_to_text_configured": stt is not None and stt.is_configured(),
            "note": (
                "TeXML Gather is the default production path (VOICE_MODE=gather). "
                "Set VOICE_MODE=stream with STT plus Telnyx/Twilio/Vonage for turn-based media streaming. "
                "Set VOICE_MODE=duplex with STT plus Telnyx/Twilio/Vonage for persistent "
                "media sessions with barge-in."
            ),
        }
