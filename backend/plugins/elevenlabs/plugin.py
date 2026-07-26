"""ElevenLabs text-to-speech plugin."""

from __future__ import annotations

from app.config import get_settings
from app.plugins.interfaces import TextToSpeechPlugin
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps
from plugins.elevenlabs.manifest import MANIFEST
from plugins.elevenlabs.services import ElevenLabsSpeechService


class ElevenLabsPlugin(TextToSpeechPlugin):
    def __init__(self) -> None:
        self._service = ElevenLabsSpeechService()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        caps = ProviderCapabilities(
            provider_name="elevenlabs",
            ai_voice=True,
            country_support=frozenset({"*"}),
        )
        return runtime_caps(caps, self, service="text_to_speech")

    def is_configured(self) -> bool:
        return bool(get_settings().elevenlabs_api_key)

    async def synthesize(
        self,
        text: str,
        *,
        language: str = "en-US",
        output_format: str | None = None,
    ) -> bytes:
        return await self._service.synthesize(text, language=language, output_format=output_format)


def create_plugin() -> ElevenLabsPlugin:
    return ElevenLabsPlugin()
