"""Telnyx TeXML response builders for voice conversations."""

from html import escape
from urllib.parse import urlencode

VOICE = "Polly.Joanna"
LANGUAGE = "en-US"


def _voice_urls(base_url: str, call_log_id: str) -> dict[str, str]:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return {
        "gather": f"{prefix}/gather?{params}",
        "status": f"{prefix}/status?{params}",
        "beep": f"{prefix}/beep.wav",
    }


def _say(message: str) -> str:
    text = escape(message, quote=False)
    return f'<Say voice="{VOICE}" language="{LANGUAGE}">{text}</Say>'


def build_say_and_gather(
    message: str,
    base_url: str,
    call_log_id: str,
    *,
    include_beep: bool = True,
) -> str:
    """
    Speak the message, play a short beep, then listen for speech.
    Say is outside Gather so the caller hears the full prompt before the tone.
    """
    urls = _voice_urls(base_url, call_log_id)
    gather_url = escape(urls["gather"], quote=True)
    beep = ""
    if include_beep:
        beep_url = escape(urls["beep"], quote=True)
        # Play beep after the prompt, before Gather opens the mic.
        beep = f'<Play loop="1">{beep_url}</Play>'

    no_input = _say("I didn't catch that. Goodbye!")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(message)}"
        f"{beep}"
        '<Pause length="1"/>'
        f'<Gather input="speech dtmf" action="{gather_url}" method="GET" '
        f'timeout="30" speechTimeout="5" language="{LANGUAGE}">'
        "</Gather>"
        f"{no_input}"
        "<Hangup/>"
        "</Response>"
    )


def build_greeting(business_name: str, base_url: str, call_log_id: str) -> str:
    greeting = (
        f"Thank you for calling {business_name}. "
        "I'm the AI receptionist. "
        "After the tone, tell me what's going on — "
        "for example a leak, a clogged drain, or no hot water."
    )
    return build_say_and_gather(greeting, base_url, call_log_id)


def build_transfer_texml(escalation_phone: str, message: str | None = None) -> str:
    msg = message or "Please hold while I connect you with a team member."
    phone = escape(escalation_phone.strip(), quote=False)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(msg)}"
        f'<Dial timeout="30"><Number>{phone}</Number></Dial>'
        f"{_say('Sorry, no one is available right now. We will call you back shortly.')}"
        "<Hangup/>"
        "</Response>"
    )


def build_hangup(message: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>{_say(message)}<Hangup/></Response>"
    )


def build_empty_response() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
