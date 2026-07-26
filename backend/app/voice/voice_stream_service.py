"""CPaaS media stream + speech-to-text plugin for lower-latency voice (VOICE_MODE=stream)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import WebSocket

from app.config import get_settings
from app.dependencies.plugins import get_speech_to_text_plugin
from app.database import SessionLocal
from app.domain.telecom import resolve_voice_locale
from app.models import Business, CallLog
from app.providers.factory import get_call_service
from app.services.voice_mode_service import VoiceModeService
from app.voice.duplex.contracts import MediaEventType
from app.voice.duplex.media_utils import parse_json_media_message
from app.voice.duplex.vonage_media_utils import parse_vonage_binary_media, parse_vonage_text_message
from app.voice.gather_handler import handle_gather_result
from app.voice.voice_markup import get_voice_markup
from app.plugins.interfaces import SpeechToTextPlugin

logger = logging.getLogger(__name__)

STREAM_LISTEN_SECONDS = 45

_PROVIDER_STT: dict[str, tuple[str, int]] = {
    "telnyx": ("mulaw", 8000),
    "twilio": ("mulaw", 8000),
    "vonage": ("linear16", 16000),
}


async def _audio_from_json_stream(websocket: WebSocket, *, provider_name: str) -> AsyncIterator[bytes]:
    """Yield PCMU/mulaw RTP payloads from Telnyx or Twilio media stream frames."""
    while True:
        raw = await websocket.receive_text()
        event = parse_json_media_message(raw, provider_name=provider_name)
        if event is None:
            continue
        if event.event_type == MediaEventType.MEDIA and event.audio_payload:
            yield event.audio_payload
        elif event.event_type == MediaEventType.STOP:
            break


async def _audio_from_vonage_stream(websocket: WebSocket) -> AsyncIterator[bytes]:
    """Yield L16 PCM from Vonage binary WebSocket media."""
    while True:
        message = await websocket.receive()
        if message.get("type") == "websocket.disconnect":
            break
        payload = message.get("bytes")
        if payload:
            event = parse_vonage_binary_media(payload)
            if event and event.audio_payload:
                yield event.audio_payload
            continue
        raw_text = message.get("text")
        if raw_text:
            event = parse_vonage_text_message(raw_text)
            if event and event.event_type == MediaEventType.STOP:
                break


async def _collect_final_transcript(
    audio_stream: AsyncIterator[bytes],
    stt_plugin: SpeechToTextPlugin,
    *,
    language: str = "en-US",
    encoding: str = "mulaw",
    sample_rate: int = 8000,
) -> str:
    """Run live STT via speech-to-text plugin and return the last final transcript segment."""
    final_parts: list[str] = []
    async for chunk in stt_plugin.transcribe_stream(
        audio_stream,
        language=language,
        encoding=encoding,
        sample_rate=sample_rate,
    ):
        if chunk.is_final and chunk.text.strip():
            final_parts.append(chunk.text.strip())
    return " ".join(final_parts).strip()


def _voice_country_for_call(db, call_log_id: str) -> str | None:
    call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
    if call_log is None:
        return None
    business = db.query(Business).filter(Business.id == call_log.business_id).first()
    return business.country if business else None


def _provider_for_call(db, call_log_id: str) -> str:
    call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
    return (call_log.provider if call_log and call_log.provider else "telnyx").lower()


async def process_media_stream(
    websocket: WebSocket,
    *,
    call_log_id: str,
    call_sid: str | None,
) -> None:
    """
    Accept CPaaS media stream WebSocket, transcribe via STT plugin, push next markup.
    Falls back to gather on the next turn if streaming is unavailable or fails.
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

    stt_plugin = get_speech_to_text_plugin()
    if stt_plugin is None:
        await websocket.close(code=1008, reason="Speech-to-text not configured")
        return

    db = SessionLocal()
    try:
        provider = _provider_for_call(db, call_log_id)
        country = _voice_country_for_call(db, call_log_id)
        language = resolve_voice_locale(country).language
        encoding, sample_rate = _PROVIDER_STT.get(provider, ("mulaw", 8000))
    finally:
        db.close()

    if provider == "vonage":
        audio_source = _audio_from_vonage_stream(websocket)
    else:
        audio_source = _audio_from_json_stream(websocket, provider_name=provider)

    try:
        transcript = await asyncio.wait_for(
            _collect_final_transcript(
                audio_source,
                stt_plugin,
                language=language,
                encoding=encoding,
                sample_rate=sample_rate,
            ),
            timeout=STREAM_LISTEN_SECONDS,
        )
    except TimeoutError:
        logger.info("Media stream listen timed out", extra={"call_log_id": call_log_id})
        transcript = ""
    except Exception:
        logger.exception("Stream transcription failed", extra={"call_log_id": call_log_id})
        transcript = ""
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

    db = SessionLocal()
    try:
        call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        business = (
            db.query(Business).filter(Business.id == call_log.business_id).first()
            if call_log
            else None
        )
        provider = _provider_for_call(db, call_log_id)
        markup_builder = get_voice_markup(provider)
        if transcript:
            markup = await handle_gather_result(db, call_log_id, transcript, None)
        else:
            markup = markup_builder.build_say_and_gather(
                "Sorry, I didn't catch that. After the tone, please try again.",
                settings.public_api_url,
                call_log_id,
                call_sid=call_sid,
                country=country,
            )
        call_service = get_call_service(
            business=business,
            db=db,
            resource_provider=call_log.provider if call_log else None,
        )
        await call_service.answer_call(call_sid, texml=markup)
        logger.info(
            "Stream turn completed",
            extra={"call_log_id": call_log_id, "transcript_len": len(transcript), "provider": provider},
        )
    except Exception:
        logger.exception("Failed to advance call after media stream", extra={"call_log_id": call_log_id})
        try:
            fallback = get_voice_markup(_provider_for_call(db, call_log_id)).build_say_and_gather(
                "Sorry, something went wrong. After the tone, please repeat that.",
                settings.public_api_url,
                call_log_id,
                call_sid=call_sid,
                country=country,
            )
            await get_call_service(
                business=business,
                db=db,
                resource_provider=call_log.provider if call_log else None,
            ).answer_call(call_sid, texml=fallback)
        except Exception:
            logger.exception("Stream fallback markup failed", extra={"call_log_id": call_log_id})
    finally:
        db.close()


async def process_telnyx_media_stream(
    websocket: WebSocket,
    *,
    call_log_id: str,
    call_sid: str | None,
) -> None:
    """Backward-compatible alias for Telnyx stream processing."""
    await process_media_stream(
        websocket,
        call_log_id=call_log_id,
        call_sid=call_sid,
    )
