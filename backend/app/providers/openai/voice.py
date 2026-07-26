"""OpenAI voice adapter — STT/TTS for stream mode and future realtime."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from app.config import get_settings
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import openai_voice, runtime_caps
from app.providers.exceptions import ProviderUnavailableError
from app.providers.voice import TranscriptSegment, VoiceProvider

logger = logging.getLogger(__name__)

OPENAI_API_BASE = "https://api.openai.com/v1"


class OpenAIVoiceProvider(VoiceProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(openai_voice(), self, service="voice")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {get_settings().openai_api_key}"}

    async def speech_to_text(self, audio_bytes: bytes, *, language: str = "en") -> str:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_API_BASE}/audio/transcriptions",
                headers=self._headers(),
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                data={"model": "whisper-1", "language": language},
            )
            response.raise_for_status()
            return response.json().get("text", "")

    async def text_to_speech(self, text: str, *, voice: str = "alloy") -> bytes:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_API_BASE}/audio/speech",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"model": "tts-1", "input": text, "voice": voice},
            )
            response.raise_for_status()
            return response.content

    async def realtime_stream(
        self, audio_stream: AsyncIterator[bytes], *, language: str = "en"
    ) -> AsyncIterator[TranscriptSegment]:
        """Batch chunks for Whisper — full realtime WebSocket deferred to stream handler."""
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
        if buffer:
            text = await self.speech_to_text(bytes(buffer), language=language)
            if text.strip():
                yield TranscriptSegment(text=text.strip(), is_final=True)
