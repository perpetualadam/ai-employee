"""Telnyx media stream WebSocket frame helpers — vendor-specific, used by duplex adapter only."""

from __future__ import annotations

import base64
import json


def build_outbound_mp3_frame(audio_mp3: bytes) -> str:
    """Send a complete MP3 clip for Telnyx bidirectionalMode=mp3 playback."""
    payload = base64.b64encode(audio_mp3).decode("ascii")
    return json.dumps({"event": "media", "media": {"payload": payload}})


def build_outbound_rtp_frame(rtp_payload: bytes) -> str:
    """Send a PCMU/PCMA RTP payload for Telnyx bidirectionalMode=rtp playback."""
    payload = base64.b64encode(rtp_payload).decode("ascii")
    return json.dumps({"event": "media", "media": {"payload": payload}})


def build_clear_playback_frame() -> str:
    """Stop queued/playing outbound media and flush marks (barge-in)."""
    return json.dumps({"event": "clear"})


def chunk_mulaw_frames(audio: bytes, *, frame_ms: int = 20, sample_rate: int = 8000) -> list[bytes]:
    """Split mulaw audio into ~20ms RTP-sized chunks (160 bytes at 8 kHz)."""
    bytes_per_frame = max(1, sample_rate * frame_ms // 1000)
    return [audio[i : i + bytes_per_frame] for i in range(0, len(audio), bytes_per_frame)]


def is_mp3_audio(audio: bytes, content_type: str) -> bool:
    if content_type in ("audio/mpeg", "audio/mp3"):
        return True
    if len(audio) >= 3 and audio[:3] == b"ID3":
        return True
    if len(audio) >= 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0:
        return True
    return False
