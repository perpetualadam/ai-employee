"""Telnyx TeXML response builders for voice conversations."""

from html import escape
from urllib.parse import urlencode

from app.domain.telecom import resolve_voice_locale
from app.models import Business
from app.config import get_settings

DEFAULT_VOICE = "Polly.Joanna"
DEFAULT_LANGUAGE = "en-US"


def _voice_for_country(country: str | None) -> tuple[str, str]:
    locale = resolve_voice_locale(country)
    return locale.voice, locale.language


def _voice_urls(base_url: str, call_log_id: str) -> dict[str, str]:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return {
        "gather": f"{prefix}/gather?{params}",
        "status": f"{prefix}/status?{params}",
        "beep": f"{prefix}/beep.wav",
    }


def public_ws_url(path: str) -> str:
    """Convert PUBLIC_API_URL to a WebSocket URL for CPaaS media streams."""
    base = get_settings().public_api_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://") + path
    if base.startswith("http://"):
        return "ws://" + base.removeprefix("http://") + path
    return base + path


def duplex_stream_url(call_log_id: str, call_sid: str) -> str:
    params = urlencode({"call_log_id": call_log_id, "call_sid": call_sid})
    return public_ws_url(f"/api/v1/voice/duplex/stream?{params}")


def media_stream_url(call_log_id: str, call_sid: str) -> str:
    params = urlencode({"call_log_id": call_log_id, "call_sid": call_sid})
    return public_ws_url(f"/api/v1/voice/stream?{params}")


def build_say_and_duplex(
    message: str,
    base_url: str,
    call_log_id: str,
    call_sid: str,
    *,
    country: str | None = None,
) -> str:
    """Start a persistent duplex media session via the tenant telephony CPaaS adapter."""
    from app.integrations.registry import get_duplex_media_adapter

    adapter = get_duplex_media_adapter()
    stream_url = duplex_stream_url(call_log_id, call_sid)
    return adapter.build_session_start_response(
        greeting=message,
        stream_url=stream_url,
        country=country,
    )


def _say(message: str, country: str | None = None) -> str:
    voice, language = _voice_for_country(country)
    text = escape(message, quote=False)
    return f'<Say voice="{voice}" language="{language}">{text}</Say>'


def build_say_and_stream(
    message: str,
    base_url: str,
    call_log_id: str,
    call_sid: str,
    *,
    include_beep: bool = True,
    country: str | None = None,
) -> str:
    """Speak, beep, then stream inbound audio to Deepgram via WebSocket."""
    urls = _voice_urls(base_url, call_log_id)
    stream_params = urlencode({"call_log_id": call_log_id, "call_sid": call_sid})
    stream_url = escape(public_ws_url(f"/api/v1/voice/stream?{stream_params}"), quote=True)
    beep = ""
    if include_beep:
        beep_url = escape(urls["beep"], quote=True)
        beep = f'<Play loop="1">{beep_url}</Play>'

    settings = get_settings()
    voice, language = _voice_for_country(country)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(message, country)}"
        f"{beep}"
        "<Start>"
        f'<Stream url="{stream_url}" track="inbound_track" codec="PCMU" />'
        "</Start>"
        f'<Pause length="{settings.voice_gather_timeout + 25}"/>'
        f"{_say('Sorry, I did not hear anything. Goodbye!', country)}"
        "<Hangup/>"
        "</Response>"
    )


def build_say_and_gather(
    message: str,
    base_url: str,
    call_log_id: str,
    *,
    include_beep: bool = True,
    call_sid: str | None = None,
    country: str | None = None,
) -> str:
    """
    Speak the message, play a short beep, then listen for speech.
    Uses duplex or Deepgram stream when configured; otherwise TeXML gather.
    """
    if call_sid:
        from app.services.voice_mode_service import VoiceModeService

        effective = VoiceModeService.effective_mode()
        if effective == "duplex":
            return build_say_and_duplex(
                message,
                base_url,
                call_log_id,
                call_sid,
                country=country,
            )
        if effective == "stream":
            return build_say_and_stream(
                message,
                base_url,
                call_log_id,
                call_sid,
                include_beep=include_beep,
                country=country,
            )

    urls = _voice_urls(base_url, call_log_id)
    gather_url = escape(urls["gather"], quote=True)
    settings = get_settings()
    beep = ""
    if include_beep:
        beep_url = escape(urls["beep"], quote=True)
        beep = f'<Play loop="1">{beep_url}</Play>'

    _, language = _voice_for_country(country)
    no_input = _say("I didn't catch that. Goodbye!", country)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(message, country)}"
        f"{beep}"
        f'<Gather input="speech dtmf" action="{gather_url}" method="GET" '
        f'timeout="{settings.voice_gather_timeout}" '
        f'speechTimeout="{settings.voice_gather_speech_timeout}" language="{language}">'
        "</Gather>"
        f"{no_input}"
        "<Hangup/>"
        "</Response>"
    )


def build_greeting(business: Business, base_url: str, call_log_id: str, *, call_sid: str | None = None) -> str:
    from app.domain.recording import greeting_with_recording_notice
    from app.domain.trades.registry import resolve_trade_context

    trade = resolve_trade_context(business)
    greeting = (
        f"Thank you for calling {business.name}. "
        "I'm the AI receptionist. "
        f"After the tone, tell me what's going on — for example {trade.voice_greeting_example}."
    )
    greeting = greeting_with_recording_notice(
        greeting,
        recording_enabled=bool(getattr(business, "recording_enabled", False)),
    )
    return build_say_and_gather(greeting, base_url, call_log_id, call_sid=call_sid, country=business.country)


def build_transfer_texml(escalation_phone: str, message: str | None = None, *, country: str | None = None) -> str:
    msg = message or "Please hold while I connect you with a team member."
    phone = escape(escalation_phone.strip(), quote=False)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(msg, country)}"
        f'<Dial timeout="30"><Number>{phone}</Number></Dial>'
        f"{_say('Sorry, no one is available right now. We will call you back shortly.', country)}"
        "<Hangup/>"
        "</Response>"
    )


def build_hangup(message: str, *, country: str | None = None) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>{_say(message, country)}<Hangup/></Response>"
    )


def build_empty_response() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def build_outbound_answer_texml(
    business_name: str,
    escalation_phone: str | None,
    *,
    reason: str | None = None,
    country: str | None = None,
) -> str:
    """When customer answers an outbound callback, greet and connect to the owner."""
    intro = reason or f"Hi, this is {business_name} calling about your recent service request."
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Response>",
        _say(intro, country),
    ]
    if escalation_phone:
        phone = escape(escalation_phone.strip(), quote=False)
        parts.append(_say("Connecting you now.", country))
        parts.append(f'<Dial timeout="30"><Number>{phone}</Number></Dial>')
        parts.append(_say("Sorry, we could not connect you. We will try again soon.", country))
    else:
        parts.append(
            _say("Please call us back at your convenience. Thank you.", country)
        )
    parts.append("<Hangup/>")
    parts.append("</Response>")
    return "".join(parts)

