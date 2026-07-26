"""Shared helpers for CPaaS media stream adapters."""

from __future__ import annotations

import base64
import json
from typing import Any

from app.voice.duplex.contracts import MediaEvent, MediaEventType


def parse_json_media_message(raw_text: str, *, provider_name: str) -> MediaEvent | None:
    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    event = (data.get("event") or "").lower()
    if event == "media":
        payload = (data.get("media") or {}).get("payload") or ""
        if not payload:
            return None
        return MediaEvent(
            event_type=MediaEventType.MEDIA,
            audio_payload=base64.b64decode(payload),
            call_id=_extract_call_id(data),
            stream_id=_extract_stream_id(data),
            raw=data,
        )
    if event in ("stop", "close"):
        return MediaEvent(
            event_type=MediaEventType.STOP,
            call_id=_extract_call_id(data),
            stream_id=_extract_stream_id(data),
            raw=data,
        )
    if event == "start":
        return MediaEvent(
            event_type=MediaEventType.START,
            call_id=_extract_call_id(data),
            stream_id=_extract_stream_id(data),
            raw=data,
        )
    return None


def _extract_call_id(data: dict[str, Any]) -> str | None:
    start = data.get("start") or {}
    if start.get("call_control_id"):
        return str(start["call_control_id"])
    for key in ("callSid", "call_sid", "call_control_id", "callControlId"):
        if data.get(key):
            return str(data[key])
    start = data.get("start") or {}
    for key in ("callSid", "call_sid", "call_control_id"):
        if start.get(key):
            return str(start[key])
    return None


def _extract_stream_id(data: dict[str, Any]) -> str | None:
    if data.get("stream_id"):
        return str(data["stream_id"])
    start = data.get("start") or {}
    if start.get("streamSid"):
        return str(start["streamSid"])
    if start.get("stream_sid"):
        return str(start["stream_sid"])
    return None
