"""Deepgram STT adapter — vendor SDK usage isolated in plugin layer."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.voice.provider import TranscriptChunk
from app.voice.stt.deepgram_stt import DeepgramSTT


class DeepgramSpeechService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _api_key(self) -> str:
        key = self._settings.deepgram_api_key
        if not key:
            raise RuntimeError("DEEPGRAM_API_KEY is not configured")
        return key

    async def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={"Authorization": f"Token {self._api_key()}"},
                content=audio_bytes,
                params={"language": language},
            )
            response.raise_for_status()
            data = response.json()
        return data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get(
            "transcript",
            "",
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        *,
        language: str = "en-US",
        encoding: str = "mulaw",
        sample_rate: int = 8000,
    ) -> AsyncIterator[TranscriptChunk]:
        stt = DeepgramSTT(self._api_key(), language=language)
        async for chunk in stt.transcribe_stream(audio_stream, encoding=encoding, sample_rate=sample_rate):
            yield chunk
