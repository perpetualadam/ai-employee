"""Process Telnyx Gather webhook results into the next TeXML response."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.intake import normalize_caller_speech
from app.models import Business
from app.voice.call_service import get_call_log, process_speech_turn
from app.voice.gather_prompts import (
    empty_gather_prompt,
    is_low_confidence_speech,
    is_unreliable_speech,
    low_confidence_gather_prompt,
    truncated_gather_prompt,
)
from app.voice.stt.gather_stt import GatherSpeechSTT
from app.voice.texml_builder import build_hangup, build_say_and_gather


async def handle_gather_result(
    db: Session,
    call_log_id: str,
    speech_result: str | None,
    confidence: str | None = None,
) -> str:
    """Process Gather speech result and return next TeXML."""
    call_log = get_call_log(db, call_log_id)
    if call_log is None:
        return build_hangup("Sorry, this session has expired. Goodbye.")

    business = db.query(Business).filter(Business.id == call_log.business_id).first()
    if business is None:
        return build_hangup("Sorry, this business is not available. Goodbye.")

    settings = get_settings()

    if GatherSpeechSTT.is_empty(speech_result):
        return build_say_and_gather(
            empty_gather_prompt(call_log),
            settings.public_api_url,
            call_log.id,
        )

    chunk = GatherSpeechSTT.from_speech_result(
        speech_result or "",
        float(confidence) if confidence else None,
    )
    speech_confidence = getattr(chunk, "confidence", None)

    if is_unreliable_speech(chunk.text, speech_confidence, call_log):
        if is_low_confidence_speech(chunk.text, speech_confidence):
            retry_prompt = low_confidence_gather_prompt(call_log)
        else:
            retry_prompt = truncated_gather_prompt(call_log)
        return build_say_and_gather(
            retry_prompt,
            settings.public_api_url,
            call_log.id,
        )

    speech_text = normalize_caller_speech(chunk.text)
    texml, _ = await process_speech_turn(db, call_log, business, speech_text)
    return texml
