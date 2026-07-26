"""Duplex media WebSocket handler — multi-provider STT + barge-in orchestration."""

from __future__ import annotations

import logging

from fastapi import WebSocket

from app.database import SessionLocal
from app.dependencies.plugins import get_speech_to_text_plugin, get_text_to_speech_plugin
from app.domain.intake import normalize_caller_speech
from app.domain.telecom import resolve_voice_locale
from app.models import Business, CallLog
from app.services.voice_mode_service import VoiceModeService
from app.voice.call_service import get_call_log, process_duplex_turn
from app.voice.duplex.resolver import get_duplex_media_adapter
from app.voice.duplex.session import DuplexVoiceSession
from app.voice.texml_builder import duplex_stream_url

logger = logging.getLogger(__name__)


async def handle_duplex_stream(
    websocket: WebSocket,
    *,
    call_log_id: str,
    call_sid: str | None,
) -> None:
    """Accept a CPaaS media WebSocket and run a persistent duplex voice session."""
    if not VoiceModeService.duplex_available():
        mode = VoiceModeService.status()
        reason = (
            "Duplex voice unavailable. "
            f"Effective mode: {mode['effective_mode']}. "
            "Set VOICE_MODE=duplex with STT and a configured telephony CPaaS."
        )
        logger.info("Duplex stream rejected", extra={"call_log_id": call_log_id, "mode": mode})
        await websocket.accept()
        await websocket.close(code=1008, reason=reason[:120])
        return

    if not call_sid:
        await websocket.accept()
        await websocket.close(code=1008, reason="Missing call_sid")
        return

    stt = get_speech_to_text_plugin()
    if stt is None or not stt.is_configured():
        await websocket.accept()
        await websocket.close(code=1008, reason="Speech-to-text not configured")
        return

    db = SessionLocal()
    try:
        call_log = get_call_log(db, call_log_id)
        if call_log is None:
            await websocket.accept()
            await websocket.close(code=1008, reason="Unknown call session")
            return

        business = db.query(Business).filter(Business.id == call_log.business_id).first()
        if business is None:
            await websocket.accept()
            await websocket.close(code=1008, reason="Business not found")
            return

        adapter = get_duplex_media_adapter(business=business, db=db)
        if adapter is None:
            await websocket.accept()
            await websocket.close(code=1008, reason="Duplex adapter not configured")
            return

        stream_url = duplex_stream_url(call_log_id, call_sid)
        language = resolve_voice_locale(business.country).language
        country = business.country

        async def on_final_transcript(transcript: str) -> str:
            speech_text = normalize_caller_speech(transcript, business.industry)
            db.refresh(call_log)
            turn = await process_duplex_turn(db, call_log, business, speech_text)

            if turn.action == "hangup":
                markup = adapter.build_hangup_response(turn.reply, country=country)
                await adapter.push_markup(call_sid, markup)
                return turn.reply

            if turn.action == "transfer" and turn.transfer_to:
                markup = adapter.build_transfer_response(
                    turn.transfer_to,
                    turn.reply,
                    country=country,
                )
                await adapter.push_markup(call_sid, markup)
                return turn.reply

            audio_delivered = False
            playback_format = adapter.preferred_playback_content_type()
            if tts_plugin := get_text_to_speech_plugin():
                if tts_plugin.is_configured() and turn.reply.strip():
                    audio = await tts_plugin.synthesize(
                        turn.reply,
                        language=language,
                        output_format=playback_format,
                    )
                    if audio:
                        audio_delivered = await adapter.deliver_audio(
                            call_sid,
                            audio,
                            content_type=playback_format,
                        )

            if audio_delivered and adapter.supports_websocket_playback():
                # Phase 2: persistent stream stays open — no TeXML Say re-attach needed.
                return turn.reply

            markup = adapter.build_reply_response(
                message=turn.reply,
                stream_url=stream_url,
                country=country,
            )
            await adapter.push_markup(call_sid, markup)
            return turn.reply

        session = DuplexVoiceSession(
            adapter=adapter,
            stt=stt,
            tts=get_text_to_speech_plugin(),
            call_id=call_sid,
            call_log_id=call_log_id,
            language=language,
            on_final_transcript=on_final_transcript,
        )
        await session.run(websocket)
    except Exception:
        logger.exception("Duplex stream handler failed", extra={"call_log_id": call_log_id})
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        db.close()
