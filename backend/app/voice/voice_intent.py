"""Backward-compatible re-exports — see app.voice.conversation and app.voice.gather_prompts."""

from app.domain.call import call_has_booking
from app.voice.conversation import is_closing_acknowledgment, is_farewell
from app.voice.gather_prompts import (
    empty_gather_prompt,
    is_truncated_speech,
    truncated_gather_prompt,
)

__all__ = [
    "call_has_booking",
    "empty_gather_prompt",
    "is_closing_acknowledgment",
    "is_farewell",
    "is_truncated_speech",
    "truncated_gather_prompt",
]
