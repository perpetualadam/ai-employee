"""Call recording disclosure and retention helpers (pure domain)."""

RECORDING_DISCLOSURE = (
    "This call may be recorded so our team can review details if needed."
)

# Providers whose voice markup supports TeXML/TwiML <Start><Recording/>.
XML_RECORDING_PROVIDERS = frozenset({"telnyx", "twilio", "signalwire"})


def greeting_with_recording_notice(greeting: str, *, recording_enabled: bool) -> str:
    """Prepend a short recording notice when retention recording is on."""
    text = (greeting or "").strip()
    if not recording_enabled or not text:
        return greeting
    if RECORDING_DISCLOSURE.lower() in text.lower():
        return text
    return f"{RECORDING_DISCLOSURE} {text}"


def supports_xml_call_recording(provider: str | None) -> bool:
    return (provider or "").strip().lower() in XML_RECORDING_PROVIDERS
