"""Twilio Media Streams WebSocket handler for real-time STT."""

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.ai.receptionist_agent import ReceptionistAgent, get_ai_provider
from app.config import get_settings
from app.database import SessionLocal
from app.models import Business, CallLog
from app.voice.call_service import get_call_log
from app.voice.stt.deepgram_stt import DeepgramSTT
from app.voice.tts.twilio_tts import TwilioSayTTS
from app.voice.twilio_client import get_twilio_client
from app.voice.twiml_builder import build_say_and_gather, build_transfer_twiml

logger = logging.getLogger(__name__)

# Buffer utterances per stream until Deepgram marks them final
_utterance_buffers: dict[str, list[str]] = {}


async def _audio_chunk_iterator(queue: asyncio.Queue[bytes | None]) -> AsyncIterator[bytes]:
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield chunk


class MediaStreamHandler:
    """Handles Twilio Media Stream WebSocket connections."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid: str | None = None
        self.call_sid: str | None = None
        self.call_log_id: str | None = None
        self.audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def run(self) -> None:
        await self.websocket.accept()
        logger.info("Media stream WebSocket connected")

        settings = get_settings()
        deepgram: DeepgramSTT | None = None
        if settings.deepgram_api_key:
            deepgram = DeepgramSTT(settings.deepgram_api_key)

        transcribe_task: asyncio.Task | None = None

        try:
            while True:
                raw = await self.websocket.receive_text()
                message = json.loads(raw)
                event = message.get("event")

                if event == "connected":
                    logger.debug("Media stream connected event")

                elif event == "start":
                    self.stream_sid = message["start"]["streamSid"]
                    self.call_sid = message["start"]["callSid"]
                    custom = message["start"].get("customParameters", {})
                    self.call_log_id = custom.get("call_log_id")
                    logger.info(
                        "Media stream started",
                        extra={"stream_sid": self.stream_sid, "call_log_id": self.call_log_id},
                    )

                    if deepgram and self.call_log_id:
                        transcribe_task = asyncio.create_task(
                            self._process_deepgram(deepgram)
                        )

                elif event == "media":
                    payload = message["media"]["payload"]
                    audio = base64.b64decode(payload)
                    if deepgram:
                        await self.audio_queue.put(audio)

                elif event == "stop":
                    logger.info("Media stream stopped", extra={"stream_sid": self.stream_sid})
                    await self.audio_queue.put(None)
                    if transcribe_task:
                        await transcribe_task
                    break

        except WebSocketDisconnect:
            logger.info("Media stream WebSocket disconnected")
        finally:
            await self.audio_queue.put(None)

    async def _process_deepgram(self, deepgram: DeepgramSTT) -> None:
        """Transcribe audio and respond when utterances are final."""
        buffer_key = self.call_log_id or str(uuid4())
        _utterance_buffers.setdefault(buffer_key, [])

        try:
            async for chunk in deepgram.transcribe_stream(_audio_chunk_iterator(self.audio_queue)):
                if not chunk.is_final:
                    continue
                await self._handle_final_transcript(chunk.text)
        except Exception:
            logger.exception("Deepgram transcription failed")

    async def _handle_final_transcript(self, text: str) -> None:
        if not self.call_log_id or not self.call_sid:
            return

        db = SessionLocal()
        try:
            call_log = get_call_log(db, self.call_log_id)
            if call_log is None:
                return

            business = db.query(Business).filter(Business.id == call_log.business_id).first()
            if business is None:
                return

            settings = get_settings()
            history: list[dict[str, str]] = list(call_log.conversation_history or [])

            agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=call_log.id)
            result = await agent.chat(text, history, voice_mode=True)

            reply = TwilioSayTTS.prepare_for_speech(result["reply"])
            db.refresh(call_log)
            call_log.escalated = result["escalated"]
            db.commit()

            client = get_twilio_client()
            if client is None:
                return

            if result["escalated"]:
                escalation = business.escalation_phone or business.phone_number
                twiml = (
                    build_transfer_twiml(escalation)
                    if escalation
                    else build_say_and_gather(
                        "I've notified our team. Someone will call you back shortly. Goodbye!",
                        settings.public_api_url,
                        call_log.id,
                    )
                )
            else:
                twiml = build_say_and_gather(reply, settings.public_api_url, call_log.id)

            client.calls(self.call_sid).update(twiml=twiml)
            logger.info("Updated call with AI response", extra={"call_sid": self.call_sid})

        except Exception:
            logger.exception("Failed to process media stream transcript")
        finally:
            db.close()


async def handle_media_stream(websocket: WebSocket) -> None:
    handler = MediaStreamHandler(websocket)
    await handler.run()
