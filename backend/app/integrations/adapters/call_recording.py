"""Call recording adapters — TeXML/TwiML, NCCO, and PlivoXML."""

from __future__ import annotations

import json
import logging
from html import escape
from urllib.parse import urlencode

import httpx

from app.integrations.contracts import CallRecordingAdapter, NormalizedRecordingEvent

logger = logging.getLogger(__name__)


def recording_status_callback_url(base_url: str, call_log_id: str) -> str:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return f"{prefix}/recording-status?{params}"


def _parse_duration(raw: str | None) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _first(params: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (params.get(key) or "").strip()
        if value:
            return value
    return ""


class UnsupportedCallRecordingAdapter(CallRecordingAdapter):
    """No-op for CPaaS that cannot start recording from answer markup (e.g. VoIP.ms)."""

    def __init__(self, provider_name: str = "unsupported") -> None:
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def supports_inline_recording(self) -> bool:
        return False

    def inject_recording(self, markup: str, *, base_url: str, call_log_id: str) -> str:
        del base_url, call_log_id
        return markup

    def normalize_webhook(self, params: dict[str, str]) -> NormalizedRecordingEvent:
        return NormalizedRecordingEvent(
            status=_first(params, "RecordingStatus", "recording_status", "status") or "absent",
            recording_url=_first(params, "RecordingUrl", "recording_url") or None,
            recording_id=_first(params, "RecordingSid", "recording_sid", "RecordingId") or None,
            duration_seconds=_parse_duration(
                _first(params, "RecordingDuration", "recording_duration") or None
            ),
        )


class TexmlTwimlCallRecordingAdapter(CallRecordingAdapter):
    """Telnyx TeXML / Twilio TwiML / SignalWire cXML <Start><Recording/>."""

    def __init__(self, provider_name: str) -> None:
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def inject_recording(self, markup: str, *, base_url: str, call_log_id: str) -> str:
        if "<Response>" not in markup or "<Recording" in markup:
            return markup
        callback = escape(recording_status_callback_url(base_url, call_log_id), quote=True)
        fragment = (
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
        return markup.replace("<Response>", f"<Response>{fragment}", 1)

    def normalize_webhook(self, params: dict[str, str]) -> NormalizedRecordingEvent:
        status = (_first(params, "RecordingStatus", "recording_status") or "completed").lower()
        return NormalizedRecordingEvent(
            status=status,
            recording_url=_first(params, "RecordingUrl", "recording_url", "RecordingUrl0") or None,
            recording_id=_first(params, "RecordingSid", "recording_sid", "RecordingId") or None,
            duration_seconds=_parse_duration(
                _first(params, "RecordingDuration", "recording_duration") or None
            ),
        )

    def download_recording(self, url: str) -> tuple[bytes, str]:
        from app.config import get_settings

        settings = get_settings()
        auth: tuple[str, str] | None = None
        if self._provider_name == "twilio" and settings.twilio_account_sid and settings.twilio_auth_token:
            auth = (settings.twilio_account_sid, settings.twilio_auth_token)
        elif (
            self._provider_name == "signalwire"
            and settings.signalwire_project_id
            and settings.signalwire_api_token
        ):
            auth = (settings.signalwire_project_id, settings.signalwire_api_token)

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url, auth=auth)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            if not content_type.startswith("audio/"):
                # Twilio often returns audio/x-wav or omits type for .mp3
                if url.rstrip("/").endswith(".wav"):
                    content_type = "audio/wav"
                else:
                    content_type = "audio/mpeg"
            return response.content, content_type


class VonageCallRecordingAdapter(CallRecordingAdapter):
    """Vonage NCCO asynchronous `record` action."""

    @property
    def provider_name(self) -> str:
        return "vonage"

    def inject_recording(self, markup: str, *, base_url: str, call_log_id: str) -> str:
        try:
            actions = json.loads(markup)
        except json.JSONDecodeError:
            return markup
        if not isinstance(actions, list):
            return markup
        if any(isinstance(a, dict) and a.get("action") == "record" for a in actions):
            return markup
        callback = recording_status_callback_url(base_url, call_log_id)
        record_action = {
            "action": "record",
            "eventUrl": [callback],
            "eventMethod": "POST",
            "split": "conversation",
            "channels": 2,
            "format": "mp3",
        }
        return json.dumps([record_action, *actions])

    def normalize_webhook(self, params: dict[str, str]) -> NormalizedRecordingEvent:
        # Vonage recording events use recording_url / recording_uuid / size.
        url = _first(params, "recording_url", "RecordingUrl", "recordingUrl")
        recording_id = _first(
            params, "recording_uuid", "RecordingSid", "recording_id", "conversation_uuid"
        )
        duration = _parse_duration(
            _first(params, "size", "RecordingDuration", "recording_duration", "duration") or None
        )
        # Vonage "size" is bytes, not seconds — only treat as duration when key looks like duration.
        if "size" in params and "RecordingDuration" not in params and "duration" not in params:
            duration = None
        status = (_first(params, "status", "RecordingStatus") or ("completed" if url else "absent")).lower()
        if url and status in ("", "ok"):
            status = "completed"
        return NormalizedRecordingEvent(
            status=status,
            recording_url=url or None,
            recording_id=recording_id or None,
            duration_seconds=duration,
        )

    def download_recording(self, url: str) -> tuple[bytes, str]:
        from app.voice.vonage_client import voice_auth_headers

        headers = voice_auth_headers()
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            if not content_type.startswith("audio/"):
                content_type = "audio/mpeg"
            return response.content, content_type


class PlivoCallRecordingAdapter(CallRecordingAdapter):
    """PlivoXML background session recording."""

    @property
    def provider_name(self) -> str:
        return "plivo"

    def inject_recording(self, markup: str, *, base_url: str, call_log_id: str) -> str:
        if "<Response>" not in markup:
            return markup
        if 'recordSession="true"' in markup or "recordSession='true'" in markup:
            return markup
        callback = escape(recording_status_callback_url(base_url, call_log_id), quote=True)
        fragment = (
            f'<Record recordSession="true" redirect="false" '
            f'callbackUrl="{callback}" callbackMethod="POST" '
            'recordChannelType="stereo"/>'
        )
        return markup.replace("<Response>", f"<Response>{fragment}", 1)

    def normalize_webhook(self, params: dict[str, str]) -> NormalizedRecordingEvent:
        url = _first(params, "RecordUrl", "RecordingUrl", "recording_url")
        recording_id = _first(params, "RecordingID", "RecordingSid", "recording_id")
        duration = _parse_duration(
            _first(params, "RecordingDuration", "recording_duration") or None
        )
        status = (_first(params, "RecordingStatus", "recording_status") or ("completed" if url else "absent")).lower()
        return NormalizedRecordingEvent(
            status=status,
            recording_url=url or None,
            recording_id=recording_id or None,
            duration_seconds=duration,
        )

    def download_recording(self, url: str) -> tuple[bytes, str]:
        from app.config import get_settings

        settings = get_settings()
        auth = None
        if settings.plivo_auth_id and settings.plivo_auth_token:
            auth = (settings.plivo_auth_id, settings.plivo_auth_token)
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url, auth=auth)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            if not content_type.startswith("audio/"):
                content_type = "audio/mpeg"
            return response.content, content_type


def build_call_recording_adapter(provider: str | None) -> CallRecordingAdapter:
    name = (provider or "").strip().lower()
    if name in {"telnyx", "twilio", "signalwire"}:
        return TexmlTwimlCallRecordingAdapter(name)
    if name == "vonage":
        return VonageCallRecordingAdapter()
    if name == "plivo":
        return PlivoCallRecordingAdapter()
    return UnsupportedCallRecordingAdapter(name or "unsupported")
