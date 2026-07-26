"""Twilio Media Streams WebSocket frame helpers — vendor-specific."""

from __future__ import annotations

import base64
import json


def build_outbound_mulaw_frame(*, stream_sid: str, mulaw_audio: bytes) -> str:
    payload = base64.b64encode(mulaw_audio).decode("ascii")
    return json.dumps(
        {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        }
    )


def build_clear_playback_frame(*, stream_sid: str) -> str:
    return json.dumps({"event": "clear", "streamSid": stream_sid})


def chunk_mulaw_frames(audio: bytes, *, frame_ms: int = 20, sample_rate: int = 8000) -> list[bytes]:
    bytes_per_frame = max(1, sample_rate * frame_ms // 1000)
    return [audio[i : i + bytes_per_frame] for i in range(0, len(audio), bytes_per_frame)]
