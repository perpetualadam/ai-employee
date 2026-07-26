"""OpenAI voice AI plugin."""

from __future__ import annotations

from app.plugins.interfaces import VoicePlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import openai_voice, runtime_caps
from app.providers.openai.voice import OpenAIVoiceProvider
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from plugins.openai.manifest import MANIFEST


class OpenAIPlugin(VoicePlugin):
    def __init__(self) -> None:
        self._voice = OpenAIVoiceProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(openai_voice(), self._voice, service="voice")

    def is_configured(self) -> bool:
        return self._voice.is_configured()

    def get_voice_provider(self) -> BaseProvider:
        return self._voice

    def register_providers(self, registry: ProviderRegistry) -> None:
        registry.register(ProviderService.VOICE, self._voice)


def create_plugin() -> OpenAIPlugin:
    return OpenAIPlugin()
