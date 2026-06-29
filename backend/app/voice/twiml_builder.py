"""Twilio TwiML response builders for voice conversations."""

from urllib.parse import urlencode

from twilio.twiml.voice_response import Dial, Gather, VoiceResponse

VOICE = "Polly.Joanna"
LANGUAGE = "en-US"


def _voice_urls(base_url: str, call_log_id: str) -> dict[str, str]:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return {
        "gather": f"{prefix}/gather?{params}",
        "status": f"{prefix}/status?{params}",
    }


def build_say_and_gather(
    message: str,
    base_url: str,
    call_log_id: str,
    *,
    include_prompt: bool = True,
) -> str:
    """Speak a message then listen for caller speech (Twilio STT)."""
    urls = _voice_urls(base_url, call_log_id)
    response = VoiceResponse()

    response.say(message, voice=VOICE, language=LANGUAGE)

    gather = Gather(
        input="speech",
        action=urls["gather"],
        method="POST",
        speech_timeout="auto",
        language=LANGUAGE,
        speech_model="phone_call",
    )
    if include_prompt:
        gather.say("I'm listening.", voice=VOICE, language=LANGUAGE)
    response.append(gather)

    response.say("I didn't catch that. Goodbye!", voice=VOICE, language=LANGUAGE)
    response.hangup()
    return str(response)


def build_greeting(business_name: str, base_url: str, call_log_id: str) -> str:
    greeting = (
        f"Thank you for calling {business_name}. "
        "I'm the AI receptionist. How can I help you today?"
    )
    return build_say_and_gather(greeting, base_url, call_log_id, include_prompt=False)


def build_transfer_twiml(escalation_phone: str, message: str | None = None) -> str:
    response = VoiceResponse()
    response.say(
        message or "Please hold while I connect you with a team member.",
        voice=VOICE,
        language=LANGUAGE,
    )
    dial = Dial(caller_id=None, timeout=30)
    dial.number(escalation_phone)
    response.append(dial)
    response.say(
        "Sorry, no one is available right now. We'll call you back shortly.",
        voice=VOICE,
        language=LANGUAGE,
    )
    response.hangup()
    return str(response)


def build_hangup(message: str) -> str:
    response = VoiceResponse()
    response.say(message, voice=VOICE, language=LANGUAGE)
    response.hangup()
    return str(response)


def build_media_stream_connect(stream_url: str, call_log_id: str) -> str:
    """Connect call to WebSocket media stream for real-time STT pipeline."""
    response = VoiceResponse()
    connect = response.connect()
    stream = connect.stream(url=stream_url)
    stream.parameter(name="call_log_id", value=call_log_id)
    return str(response)


def build_empty_response() -> str:
    return str(VoiceResponse())
