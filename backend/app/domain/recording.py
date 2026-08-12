"""Call recording disclosure and retention helpers (pure domain)."""

RECORDING_DISCLOSURE = (
    "This call may be recorded so our team can review details if needed."
)

# CPaaS providers that can start call recording from answer markup.
CALL_RECORDING_PROVIDERS = frozenset(
    {"telnyx", "twilio", "signalwire", "vonage", "plivo"}
)

# Backward-compatible alias — TeXML/TwiML subset of CALL_RECORDING_PROVIDERS.
XML_RECORDING_PROVIDERS = frozenset({"telnyx", "twilio", "signalwire"})


def is_retention_enabled(recording_enabled: bool | None) -> bool:
    """True when call recordings and SMS audit logs should be retained for review."""
    return bool(recording_enabled)


def greeting_with_recording_notice(greeting: str, *, recording_enabled: bool) -> str:
    """Prepend a short recording notice when retention recording is on."""
    text = (greeting or "").strip()
    if not is_retention_enabled(recording_enabled) or not text:
        return greeting
    if RECORDING_DISCLOSURE.lower() in text.lower():
        return text
    return f"{RECORDING_DISCLOSURE} {text}"


def supports_call_recording(provider: str | None) -> bool:
    return (provider or "").strip().lower() in CALL_RECORDING_PROVIDERS


def supports_xml_call_recording(provider: str | None) -> bool:
    """Deprecated alias — prefer supports_call_recording."""
    return (provider or "").strip().lower() in XML_RECORDING_PROVIDERS
