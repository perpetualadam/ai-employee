"""Duplex voice session — provider-agnostic orchestration for barge-in capable calls."""

from __future__ import annotations

import asyncio
import enum
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket

from app.voice.duplex.contracts import DuplexMediaAdapter, MediaEventType, MediaStreamBindContext

if TYPE_CHECKING:
    from app.plugins.interfaces import SpeechToTextPlugin, TextToSpeechPlugin

logger = logging.getLogger(__name__)


class SessionState(str, enum.Enum):
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    ENDED = "ended"


TranscriptHandler = Callable[[str], Awaitable[str]]


def _estimate_playback_seconds(text: str) -> float:
    words = max(1, len(text.split()))
    return max(2.0, min(45.0, words / 2.5))


class DuplexVoiceSession:
    """
    One persistent media WebSocket per call.

    Uses SpeechToTextPlugin + TextToSpeechPlugin + DuplexMediaAdapter — never vendor SDKs.
    """

    def __init__(
        self,
        *,
        adapter: DuplexMediaAdapter,
        stt: SpeechToTextPlugin,
        tts: TextToSpeechPlugin | None,
        call_id: str,
        call_log_id: str,
        language: str = "en-US",
        on_final_transcript: TranscriptHandler | None = None,
    ) -> None:
        self._adapter = adapter
        self._stt = stt
        self._tts = tts
        self._call_id = call_id
        self._call_log_id = call_log_id
        self._language = language
        self._on_final_transcript = on_final_transcript
        self._state = SessionState.LISTENING
        self._speaking = False
        self._speaking_timer: asyncio.Task[None] | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    async def run(self, websocket: WebSocket) -> None:
        await websocket.accept()
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def _audio_stream() -> AsyncIterator[bytes]:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    return
                yield chunk

        async def _pump_websocket() -> None:
            if self._adapter.uses_binary_media():
                await self._pump_binary_websocket(websocket, audio_queue)
            else:
                await self._pump_json_websocket(websocket, audio_queue)
            await audio_queue.put(None)

        pump_task = asyncio.create_task(_pump_websocket())
        stt_encoding, stt_sample_rate = self._adapter.stt_audio_encoding()
        try:
            async for chunk in self._stt.transcribe_stream(
                _audio_stream(),
                language=self._language,
                encoding=stt_encoding,
                sample_rate=stt_sample_rate,
            ):
                if not chunk.text.strip():
                    continue
                if chunk.is_final:
                    await self._handle_final_transcript(chunk.text.strip())
                elif self._state == SessionState.SPEAKING and self._adapter.supports_barge_in():
                    await self._handle_barge_in()
        except Exception:
            logger.exception(
                "Duplex session failed",
                extra={"call_log_id": self._call_log_id, "provider": self._adapter.provider_name},
            )
        finally:
            self._state = SessionState.ENDED
            self._cancel_speaking_timer()
            await self._adapter.unbind_media_websocket()
            if not pump_task.done():
                pump_task.cancel()
            try:
                await websocket.close()
            except Exception:
                pass

    async def _pump_json_websocket(
        self,
        websocket: WebSocket,
        audio_queue: asyncio.Queue[bytes | None],
    ) -> None:
        while True:
            raw = await websocket.receive_text()
            event = self._adapter.parse_media_message(raw)
            if event is None:
                continue
            if event.event_type == MediaEventType.START:
                await self._bind_stream(websocket, event)
                continue
            if event.event_type == MediaEventType.STOP:
                break
            if event.event_type == MediaEventType.MEDIA and event.audio_payload:
                await audio_queue.put(event.audio_payload)

    async def _pump_binary_websocket(
        self,
        websocket: WebSocket,
        audio_queue: asyncio.Queue[bytes | None],
    ) -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            payload = message.get("bytes")
            if payload:
                event = self._adapter.parse_binary_media(payload)
                if event and event.event_type == MediaEventType.MEDIA and event.audio_payload:
                    await audio_queue.put(event.audio_payload)
                continue
            raw = message.get("text")
            if not raw:
                continue
            event = self._adapter.parse_media_message(raw)
            if event is None:
                continue
            if event.event_type == MediaEventType.START:
                await self._bind_stream(websocket, event)
                continue
            if event.event_type == MediaEventType.STOP:
                break

    async def _bind_stream(self, websocket: WebSocket, event: Any) -> None:
        if not self._adapter.supports_websocket_playback():
            return
        start = (event.raw or {}).get("start") or {}
        media_format = start.get("media_format") or {}
        encoding = media_format.get("encoding")
        if not encoding and event.raw:
            content_type = str(event.raw.get("content-type") or "")
            if "l16" in content_type.lower():
                encoding = "L16"
        context = MediaStreamBindContext(
            call_control_id=event.call_id or start.get("call_control_id") or self._call_id,
            stream_id=event.stream_id,
            media_encoding=str(encoding or "PCMU"),
            bidirectional_mode="mp3" if self._adapter.provider_name == "telnyx" else "l16",
        )
        await self._adapter.bind_media_websocket(websocket, context=context)

    def _cancel_speaking_timer(self) -> None:
        if self._speaking_timer and not self._speaking_timer.done():
            self._speaking_timer.cancel()
        self._speaking_timer = None

    def _schedule_speaking_end(self, seconds: float) -> None:
        self._cancel_speaking_timer()
        self._speaking_timer = asyncio.create_task(self._speaking_timeout(seconds))

    async def _speaking_timeout(self, seconds: float) -> None:
        try:
            await asyncio.sleep(seconds)
            self._speaking = False
            if self._state == SessionState.SPEAKING:
                self._state = SessionState.LISTENING
        except asyncio.CancelledError:
            return

    async def _handle_barge_in(self) -> None:
        if not self._speaking:
            return
        logger.info(
            "Duplex barge-in",
            extra={"call_log_id": self._call_log_id, "provider": self._adapter.provider_name},
        )
        self._cancel_speaking_timer()
        self._speaking = False
        self._state = SessionState.LISTENING
        await self._adapter.stop_playback(self._call_id)

    async def _handle_final_transcript(self, transcript: str) -> None:
        self._state = SessionState.PROCESSING
        if self._on_final_transcript is not None:
            self._state = SessionState.SPEAKING
            self._speaking = True
            try:
                reply = await self._on_final_transcript(transcript)
            except Exception:
                self._speaking = False
                self._state = SessionState.LISTENING
                raise
            if reply.strip():
                self._schedule_speaking_end(_estimate_playback_seconds(reply))
            else:
                self._speaking = False
                self._state = SessionState.LISTENING
            return

        reply = transcript
        if self._tts and self._tts.is_configured() and reply.strip():
            self._state = SessionState.SPEAKING
            self._speaking = True
            audio = await self._tts.synthesize(reply, language=self._language)
            if audio:
                delivered = await self._adapter.deliver_audio(self._call_id, audio, content_type="audio/mpeg")
                if delivered:
                    self._schedule_speaking_end(_estimate_playback_seconds(reply))
                else:
                    self._speaking = False
            else:
                self._speaking = False

        if not self._speaking:
            self._state = SessionState.LISTENING
