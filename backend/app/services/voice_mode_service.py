"""Voice mode resolution — gather (Telnyx TeXML) vs future streaming."""

from __future__ import annotations

from app.config import get_settings
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
        return bool(
            settings.deepgram_api_key
            and telnyx_client.is_telnyx_configured()
            and settings.telnyx_texml_connection_id
            and settings.telnyx_account_sid
        )

    @staticmethod
    def status() -> dict:
        settings = get_settings()
        return {
            "requested_mode": settings.voice_mode,
            "effective_mode": VoiceModeService.effective_mode(),
            "streaming_available": VoiceModeService.streaming_available(),
            "production_recommendation": "gather",
            "deepgram_configured": bool(settings.deepgram_api_key),
            "note": (
                "Telnyx TeXML Gather is the default production path (VOICE_MODE=gather). "
                "Set VOICE_MODE=stream with DEEPGRAM_API_KEY and TELNYX_ACCOUNT_SID for "
                "lower-latency Deepgram STT via TeXML media streaming."
            ),
        }
