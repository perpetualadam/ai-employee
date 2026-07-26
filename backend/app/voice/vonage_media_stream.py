"""Vonage Voice API WebSocket helpers — vendor-specific."""

from __future__ import annotations

import json


def build_clear_command() -> str:
    return json.dumps({"action": "clear"})


def chunk_l16_frames(audio: bytes, *, frame_ms: int = 20, sample_rate: int = 16000) -> list[bytes]:
    """Split 16-bit linear PCM mono audio into ~20ms binary frames."""
    bytes_per_frame = max(2, sample_rate * frame_ms // 1000 * 2)
    if len(audio) < bytes_per_frame:
        return [audio] if audio else []
    return [audio[i : i + bytes_per_frame] for i in range(0, len(audio), bytes_per_frame)]
