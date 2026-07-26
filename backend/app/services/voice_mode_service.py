"""Voice mode resolution — gather (Telnyx TeXML) vs future streaming."""

from __future__ import annotations

from app.config import get_settings
from app.dependencies.plugins import get_speech_to_text_plugin
from app.voice import telnyx_client


class VoiceModeService:
    @staticmethod
    def effective_mode() -> str:
        """
        Return the voice mode actually used for inbound calls.
        Telnyx production path is TeXML gather; stream requires Call Control media (future).
        """
        settings = get_settings()
        requested = (settings.voice_mode or "gather").lower()
        if requested == "stream" and not VoiceModeService.streaming_available():
            return "gather"
        return requested

    @staticmethod
    def streaming_available() -> bool:
        settings = get_settings()
        stt = get_speech_to_text_plugin()
        stt_ready = stt is not None and stt.is_configured()
        return bool(
            stt_ready
            and telnyx_client.is_telnyx_configured()
            and settings.telnyx_texml_connection_id
            and settings.telnyx_account_sid
        )

    @staticmethod
    def status() -> dict:
        settings = get_settings()
        stt = get_speech_to_text_plugin()
        return {
            "requested_mode": settings.voice_mode,
            "effective_mode": VoiceModeService.effective_mode(),
            "streaming_available": VoiceModeService.streaming_available(),
            "production_recommendation": "gather",
            "speech_to_text_configured": stt is not None and stt.is_configured(),
            "note": (
                "Telnyx TeXML Gather is the default production path (VOICE_MODE=gather). "
                "Set VOICE_MODE=stream with a configured speech-to-text plugin and "
                "TELNYX_ACCOUNT_SID for lower-latency STT via TeXML media streaming."
            ),
        }
