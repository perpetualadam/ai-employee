"""Retry prompts when Telnyx Gather returns empty or truncated speech."""

import re

_NAME_Q = re.compile(r"\b(name|who am I speaking|may I ask who)\b", re.I)
_ADDRESS_Q = re.compile(r"\b(address|street|where do you|service address|property)\b", re.I)


def is_truncated_speech(text: str, confidence: float | None) -> bool:
    """Only reject obvious STT fragments — never reject single-word names or short answers."""
    cleaned = text.strip()
    if not cleaned:
        return True
    if len(cleaned) >= 15:
        return False
    words = cleaned.split()
    if len(words) == 1:
        return len(cleaned) <= 2
    if confidence is not None and confidence >= 0.35:
        return False
    if len(words) >= 3:
        return False
    if len(words) == 2 and len(cleaned) <= 12:
        return True
    return len(cleaned) <= 3


def empty_gather_prompt(call_log) -> str:
    """Context-aware retry when Telnyx returns no speech."""
    history = call_log.conversation_history or []
    has_user_turn = any(h.get("role") == "user" for h in history)

    if not has_user_turn:
        return (
            "I'm ready to help. After the tone, tell me what's wrong — "
            "for example a kitchen leak or blocked drain."
        )

    for entry in reversed(history):
        if entry.get("role") == "assistant" and entry.get("content"):
            question = entry["content"].strip()
            if _NAME_Q.search(question):
                return (
                    "Sorry, I didn't catch your name. After the tone, "
                    "please say your first and last name clearly."
                )
            if _ADDRESS_Q.search(question):
                return (
                    "Sorry, I didn't get the address. After the tone, "
                    "please say the full street address where we should come."
                )
            break

    return "Sorry, I didn't hear you. Please try again after the tone."


def truncated_gather_prompt(call_log) -> str:
    """Retry when STT only captured a fragment of the caller's sentence."""
    history = call_log.conversation_history or []
    for entry in reversed(history):
        if entry.get("role") == "assistant" and entry.get("content"):
            question = entry["content"].strip()
            if _NAME_Q.search(question):
                return (
                    "Sorry, I only caught part of that. After the tone, "
                    "please say your full first and last name."
                )
            if _ADDRESS_Q.search(question):
                return (
                    "Sorry, I only caught part of that. After the tone, "
                    "please say the complete street address."
                )
            break
    return (
        "Sorry, I only caught part of that. After the tone, "
        "please say the full sentence again."
    )
