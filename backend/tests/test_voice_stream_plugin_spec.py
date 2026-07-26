"""Specification: voice stream uses speech-to-text plugin — no direct Deepgram import."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.voice.provider import TranscriptChunk
from app.voice.voice_stream_service import _collect_final_transcript


class _MockSttPlugin:
    async def transcribe_stream(
        self,
        audio_stream,
        *,
        language: str = "en-US",
        encoding: str = "mulaw",
        sample_rate: int = 8000,
    ):
        async for _payload in audio_stream:
            yield TranscriptChunk(text="hello there", is_final=True, speaker="caller")
            break


class VoiceStreamPluginSpecification(unittest.TestCase):
    def test_voice_stream_service_has_no_deepgram_import(self) -> None:
        import app.voice.voice_stream_service as stream_module

        source = open(stream_module.__file__, encoding="utf-8").read()
        self.assertNotIn("DeepgramSTT", source)
        self.assertNotIn("deepgram_stt", source)

    def test_collect_final_transcript_delegates_to_plugin(self) -> None:
        async def _audio():
            yield b"\xff\xfe"

        async def _run() -> str:
            return await _collect_final_transcript(_audio(), _MockSttPlugin(), language="en-US")

        import asyncio

        result = asyncio.run(_run())
        self.assertEqual(result, "hello there")

    def test_process_stream_closes_when_stt_unconfigured(self) -> None:
        import asyncio

        from app.voice.voice_stream_service import process_telnyx_media_stream

        async def _run() -> None:
            with patch(
                "app.voice.voice_stream_service.get_speech_to_text_plugin",
                return_value=None,
            ):
                with patch(
                    "app.voice.voice_stream_service.VoiceModeService.streaming_available",
                    return_value=True,
                ):
                    websocket = AsyncMock()
                    await process_telnyx_media_stream(
                        websocket,
                        call_log_id="log-1",
                        call_sid="sid-1",
                    )
                    websocket.close.assert_any_call(
                        code=1008,
                        reason="Speech-to-text not configured",
                    )

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
