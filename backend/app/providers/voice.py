"""Voice AI port — STT, TTS, and realtime streaming."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

from app.providers.base import BaseProvider


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    is_final: bool
    confidence: float | None = None


class VoiceProvider(BaseProvider):
    @abstractmethod
    async def speech_to_text(self, audio_bytes: bytes, *, language: str = "en") -> str:
        ...

    @abstractmethod
    async def text_to_speech(self, text: str, *, voice: str = "alloy") -> bytes:
        ...

    @abstractmethod
    async def realtime_stream(
        self, audio_stream: AsyncIterator[bytes], *, language: str = "en"
    ) -> AsyncIterator[TranscriptSegment]:
        ...
