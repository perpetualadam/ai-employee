"""Voice AI facade — STT/TTS via VoiceProvider."""

from __future__ import annotations

from typing import AsyncIterator

from app.domain.telecom import resolve_voice_locale
from app.models import Business
from app.providers.voice import TranscriptSegment, VoiceProvider
from app.services.voice_mode_service import VoiceModeService


class VoiceService:
    def __init__(self, voice_provider: VoiceProvider) -> None:
        self._voice = voice_provider

    def mode_status(self) -> dict:
        return VoiceModeService.status()

    def locale_for_business(self, business: Business) -> dict:
        locale = resolve_voice_locale(business.country)
        return {"language": locale.language, "voice": locale.voice}

    async def transcribe(self, audio_bytes: bytes, *, business: Business) -> str:
        locale = resolve_voice_locale(business.country)
        return await self._voice.speech_to_text(audio_bytes, language=locale.language)

    async def synthesize(self, text: str, *, business: Business) -> bytes:
        locale = resolve_voice_locale(business.country)
        return await self._voice.text_to_speech(text, voice=locale.voice)

    async def stream_transcripts(
        self,
        audio_stream: AsyncIterator[bytes],
        *,
        business: Business,
    ) -> AsyncIterator[TranscriptSegment]:
        locale = resolve_voice_locale(business.country)
        async for segment in self._voice.realtime_stream(audio_stream, language=locale.language):
            yield segment

    def is_configured(self) -> bool:
        return self._voice.is_configured()
