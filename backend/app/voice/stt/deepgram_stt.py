"""Deepgram live STT for Twilio Media Streams."""

import json
import logging
from typing import AsyncIterator

import httpx

from app.voice.provider import TranscriptChunk

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramSTT:
    """Real-time speech-to-text via Deepgram streaming API."""

    def __init__(self, api_key: str, language: str = "en-US"):
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY is not configured")
        self.api_key = api_key
        self.language = language

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], *, encoding: str = "mulaw", sample_rate: int = 8000
    ) -> AsyncIterator[TranscriptChunk]:
        """
        Stream audio chunks to Deepgram and yield transcript chunks.
        Default is mulaw 8 kHz (Telnyx/Twilio); Vonage duplex uses linear16 16 kHz.
        """
        import websockets

        params = (
            f"encoding={encoding}&sample_rate={sample_rate}&channels=1"
            f"&language={self.language}&model=nova-2-phonecall"
            "&interim_results=true&endpointing=300&punctuate=true"
        )
        url = f"{DEEPGRAM_WS_URL}?{params}"

        async with websockets.connect(
            url,
            additional_headers={"Authorization": f"Token {self.api_key}"},
        ) as ws:
            async def send_audio() -> None:
                async for chunk in audio_stream:
                    await ws.send(chunk)
                await ws.send(json.dumps({"type": "CloseStream"}))

            import asyncio

            send_task = asyncio.create_task(send_audio())

            try:
                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") != "Results":
                        continue
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    if not alternatives:
                        continue
                    text = alternatives[0].get("transcript", "").strip()
                    if not text:
                        continue
                    is_final = data.get("is_final", False)
                    yield TranscriptChunk(text=text, is_final=is_final, speaker="caller")
            finally:
                send_task.cancel()

    async def transcribe_file(self, audio_bytes: bytes, content_type: str = "audio/wav") -> str:
        """Batch transcription fallback via Deepgram REST API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": content_type,
                },
                params={"model": "nova-2-phonecall", "punctuate": "true"},
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()
            return (
                data.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )
