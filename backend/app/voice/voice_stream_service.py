"""Telnyx media stream + Deepgram STT for lower-latency voice (VOICE_MODE=stream)."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator

from fastapi import WebSocket

from app.config import get_settings
from app.database import SessionLocal
from app.domain.telecom import resolve_voice_locale
from app.models import Business, CallLog
from app.services.voice_mode_service import VoiceModeService
from app.voice import telnyx_client
from app.voice.gather_handler import handle_gather_result
from app.voice.stt.deepgram_stt import DeepgramSTT
from app.voice.texml_builder import build_say_and_gather

logger = logging.getLogger(__name__)

STREAM_LISTEN_SECONDS = 45


async def _audio_from_telnyx(websocket: WebSocket) -> AsyncIterator[bytes]:
    """Yield PCMU/mulaw RTP payloads from Telnyx media stream frames."""
    while True:
        raw = await websocket.receive_text()
        data = json.loads(raw)
        event = data.get("event")
        if event == "media":
            payload = (data.get("media") or {}).get("payload") or ""
            if payload:
                yield base64.b64decode(payload)
        elif event == "stop":
            break


async def _collect_final_transcript(
    audio_stream: AsyncIterator[bytes],
    api_key: str,
    *,
    language: str = "en-US",
) -> str:
    """Run Deepgram live STT and return the last final transcript segment."""
    stt = DeepgramSTT(api_key, language=language)
    final_parts: list[str] = []
    async for chunk in stt.transcribe_stream(audio_stream):
        if chunk.is_final and chunk.text.strip():
            final_parts.append(chunk.text.strip())
    return " ".join(final_parts).strip()


def _voice_country_for_call(db, call_log_id: str) -> str | None:
    call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
    if call_log is None:
        return None
    business = db.query(Business).filter(Business.id == call_log.business_id).first()
    return business.country if business else None


async def process_telnyx_media_stream(
    websocket: WebSocket,
    *,
    call_log_id: str,
    call_sid: str | None,
) -> None:
    """
    Accept Telnyx TeXML Stream WebSocket, transcribe with Deepgram, push next TeXML.
    Falls back to TeXML Gather on the next turn if streaming is unavailable or fails.
    """
    await websocket.accept()

    if not VoiceModeService.streaming_available():
        await websocket.close(code=1008, reason="Streaming not configured")
        return

    settings = get_settings()
    if not call_sid:
        logger.warning("Media stream missing call_sid", extra={"call_log_id": call_log_id})
        await websocket.close(code=1008, reason="Missing call_sid")
        return

    db = SessionLocal()
    try:
        country = _voice_country_for_call(db, call_log_id)
        language = resolve_voice_locale(country).language
    finally:
        db.close()

    try:
        transcript = await asyncio.wait_for(
            _collect_final_transcript(
                _audio_from_telnyx(websocket),
                settings.deepgram_api_key,
                language=language,
            ),
            timeout=STREAM_LISTEN_SECONDS,
        )
    except TimeoutError:
        logger.info("Media stream listen timed out", extra={"call_log_id": call_log_id})
        transcript = ""
    except Exception:
        logger.exception("Deepgram stream transcription failed", extra={"call_log_id": call_log_id})
        transcript = ""
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

    db = SessionLocal()
    try:
        if transcript:
            texml = await handle_gather_result(db, call_log_id, transcript, None)
        else:
            texml = build_say_and_gather(
                "Sorry, I didn't catch that. After the tone, please try again.",
                settings.public_api_url,
                call_log_id,
                call_sid=call_sid,
                country=country,
            )
        telnyx_client.update_call_texml(call_sid, texml)
        logger.info(
            "Stream turn completed",
            extra={"call_log_id": call_log_id, "transcript_len": len(transcript)},
        )
    except Exception:
        logger.exception("Failed to advance call after media stream", extra={"call_log_id": call_log_id})
        try:
            fallback = build_say_and_gather(
                "Sorry, something went wrong. After the tone, please repeat that.",
                settings.public_api_url,
                call_log_id,
                call_sid=call_sid,
                country=country,
            )
            telnyx_client.update_call_texml(call_sid, fallback)
        except Exception:
            logger.exception("Stream fallback TeXML failed", extra={"call_log_id": call_log_id})
    finally:
        db.close()
