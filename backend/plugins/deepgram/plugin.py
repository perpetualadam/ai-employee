"""Deepgram speech-to-text plugin."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.config import get_settings
from app.plugins.interfaces import SpeechToTextPlugin
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps
from app.voice.provider import TranscriptChunk
from plugins.deepgram.manifest import MANIFEST
from plugins.deepgram.services import DeepgramSpeechService


class DeepgramPlugin(SpeechToTextPlugin):
    def __init__(self) -> None:
        self._service = DeepgramSpeechService()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        caps = ProviderCapabilities(
            provider_name="deepgram",
            transcriptions=True,
            realtime_media_streams=True,
            country_support=frozenset({"*"}),
        )
        return runtime_caps(caps, self, service="speech_to_text")

    def is_configured(self) -> bool:
        return bool(get_settings().deepgram_api_key)

    async def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> str:
        return await self._service.transcribe(audio_bytes, language=language)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        *,
        language: str = "en-US",
    ) -> AsyncIterator[TranscriptChunk]:
        async for chunk in self._service.transcribe_stream(audio_stream, language=language):
            yield chunk


def create_plugin() -> DeepgramPlugin:
    return DeepgramPlugin()
