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
    }


def _say(message: str) -> str:
    text = escape(message, quote=False)
    return f'<Say voice="{VOICE}" language="{LANGUAGE}">{text}</Say>'


def build_say_and_gather(
    message: str,
    base_url: str,
    call_log_id: str,
    *,
    include_prompt: bool = True,
) -> str:
    """Speak a message then listen for caller speech (Telnyx STT via Gather)."""
    urls = _voice_urls(base_url, call_log_id)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Response>",
        _say(message),
        (
            f'<Gather input="speech" action="{escape(urls["gather"], quote=True)}" '
            f'method="POST" speechTimeout="auto" language="{LANGUAGE}">'
        ),
    ]
    if include_prompt:
        parts.append(_say("I'm listening."))
    parts.extend(
        [
            "</Gather>",
            _say("I didn't catch that. Goodbye!"),
            "<Hangup/>",
            "</Response>",
        ]
    )
    return "".join(parts)


def build_greeting(business_name: str, base_url: str, call_log_id: str) -> str:
    greeting = (
        f"Thank you for calling {business_name}. "
        "I'm the AI receptionist. How can I help you today?"
    )
    return build_say_and_gather(greeting, base_url, call_log_id, include_prompt=False)


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
