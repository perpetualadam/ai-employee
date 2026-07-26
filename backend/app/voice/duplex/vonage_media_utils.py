"""Vonage Voice API WebSocket text-event parsing."""

from __future__ import annotations

import json
from typing import Any

from app.voice.duplex.contracts import MediaEvent, MediaEventType


def parse_vonage_text_message(raw_text: str) -> MediaEvent | None:
    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    event = str(data.get("event") or "")
    if event == "websocket:connected":
        return MediaEvent(
            event_type=MediaEventType.START,
            call_id=_extract_call_uuid(data),
            raw=data,
        )
    if event in ("websocket:disconnected", "websocket:closed"):
        return MediaEvent(event_type=MediaEventType.STOP, raw=data)
    if event == "websocket:cleared":
        return None
    if event == "websocket:notify":
        return None
    return None


def parse_vonage_binary_media(payload: bytes) -> MediaEvent | None:
    if not payload:
        return None
    return MediaEvent(
        event_type=MediaEventType.MEDIA,
        audio_payload=payload,
    )


def _extract_call_uuid(data: dict[str, Any]) -> str | None:
    for key in ("uuid", "call_uuid", "conversation_uuid"):
        if data.get(key):
            return str(data[key])
    return None
