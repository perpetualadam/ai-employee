"""ElevenLabs text-to-speech service."""

from __future__ import annotations

import httpx

from app.config import get_settings

_ELEVENLABS_FORMATS: dict[str, tuple[str, str]] = {
    "audio/mulaw": ("ulaw_8000", "audio/basic"),
    "ulaw_8000": ("ulaw_8000", "audio/basic"),
    "audio/l16": ("pcm_16000", "audio/pcm"),
    "pcm_16000": ("pcm_16000", "audio/pcm"),
    "audio/mpeg": ("mp3_44100_128", "audio/mpeg"),
    "audio/mp3": ("mp3_44100_128", "audio/mpeg"),
}


class ElevenLabsSpeechService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._settings.elevenlabs_api_key)

    async def synthesize(
        self,
        text: str,
        *,
        language: str = "en-US",
        output_format: str | None = None,
    ) -> bytes:
        del language
        if not self.is_configured() or not text.strip():
            return b""
        fmt_key = output_format or "audio/mpeg"
        elevenlabs_format, accept = _ELEVENLABS_FORMATS.get(fmt_key, ("mp3_44100_128", "audio/mpeg"))
        voice_id = self._settings.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={elevenlabs_format}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "xi-api-key": self._settings.elevenlabs_api_key,
                    "Accept": accept,
                },
                json={"text": text, "model_id": "eleven_monolingual_v1"},
            )
            response.raise_for_status()
            return response.content
