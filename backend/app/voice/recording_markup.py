"""Inject non-blocking call recording into TeXML/TwiML responses."""

from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from app.domain.recording import supports_xml_call_recording


def recording_status_callback_url(base_url: str, call_log_id: str) -> str:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return f"{prefix}/recording-status?{params}"


def start_recording_xml(base_url: str, call_log_id: str) -> str:
    """TeXML/TwiML fragment that starts dual-channel recording in the background."""
    callback = escape(recording_status_callback_url(base_url, call_log_id), quote=True)
    return (
        "<Start>"
        "<Recording "
        'channels="dual" '
        'track="both" '
        'format="mp3" '
        f'recordingStatusCallback="{callback}" '
        'recordingStatusCallbackMethod="POST" '
        'recordingStatusCallbackEvent="completed"'
        "/>"
        "</Start>"
    )


def with_call_recording(
    markup: str,
    *,
    base_url: str,
    call_log_id: str,
    provider: str | None,
    enabled: bool,
) -> str:
    """
    Insert <Start><Recording/></Start> after <Response> when supported.
    Safe no-op for NCCO/JSON markup or when recording is disabled.
    """
    if not enabled or not supports_xml_call_recording(provider):
        return markup
    if "<Response>" not in markup:
        return markup
    if "<Recording" in markup:
        return markup
    fragment = start_recording_xml(base_url, call_log_id)
    return markup.replace("<Response>", f"<Response>{fragment}", 1)
