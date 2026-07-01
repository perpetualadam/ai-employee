"""Retry prompts when Telnyx Gather returns empty, noisy, or truncated speech."""

import re

from app.domain.intake import extract_spoken_name

_NAME_Q = re.compile(r"\b(name|who am I speaking|may I ask who)\b", re.I)
_ADDRESS_Q = re.compile(
    r"\b(address|street|zip|zip code|where do you|service address|property)\b",
    re.I,
)
_PROBLEM_Q = re.compile(r"\b(what'?s wrong|what can I help|what seems|what'?s going|what is going)\b", re.I)

_INCOMPLETE_ENDINGS = re.compile(
    r"\b(a|an|the|is|am|my|i|have|there|can'?t|cant|would|like)\s*$",
    re.I,
)

_NOISE_ONLY = re.compile(r"^[\s\.\+]+$")


def _last_assistant_question(call_log) -> str:
    for entry in reversed(call_log.conversation_history or []):
        if entry.get("role") == "assistant" and entry.get("content"):
            return entry["content"].strip()
    return ""


def is_truncated_speech(text: str, confidence: float | None) -> bool:
    """Reject obvious STT fragments before they reach the AI agent."""
    cleaned = text.strip()
    if not cleaned or _NOISE_ONLY.fullmatch(cleaned):
        return True

    lower = cleaned.lower().rstrip(".")
    words = cleaned.split()

    if _INCOMPLETE_ENDINGS.search(lower) and len(cleaned) < 24:
        return True

    if lower in {"i have a", "i can't", "i cant", "there is a", "there's a", "call me"}:
        return True

    if len(words) == 1:
        if len(cleaned) <= 2:
            return True
        if confidence is not None and confidence < 0.45 and not cleaned.isdigit():
            return True

    if len(words) == 2 and len(cleaned) <= 12 and (confidence is None or confidence < 0.55):
        if not extract_spoken_name(cleaned):
            return True

    if len(words) >= 3 and len(cleaned) >= 15:
        return False

    if len(words) >= 3 and confidence is not None and confidence >= 0.55:
        return False

    return len(cleaned) <= 8 and (confidence is None or confidence < 0.70)


def is_low_confidence_speech(text: str, confidence: float | None) -> bool:
    """Reject very noisy recognition before it confuses the agent."""
    cleaned = text.strip()
    if not cleaned or _NOISE_ONLY.fullmatch(cleaned):
        return True
    if confidence is None:
        return False

    words = cleaned.split()
    if confidence < 0.25:
        return True
    if confidence < 0.40 and len(words) <= 2:
        return True
    if confidence < 0.50 and len(words) == 1 and len(cleaned) <= 6:
        return True
    return False


def needs_context_retry(text: str, confidence: float | None, call_log) -> bool:
    """Retry short answers that are too weak for the question just asked."""
    cleaned = text.strip()
    if not cleaned:
        return False
    if confidence is not None and confidence >= 0.80:
        return False

    question = _last_assistant_question(call_log)
    if not question:
        return False

    word_count = len(cleaned.split())
    if _ADDRESS_Q.search(question):
        if word_count <= 2 and (confidence is None or confidence < 0.75):
            return True
        if cleaned.isdigit() and word_count == 1:
            return True
    if _NAME_Q.search(question) and word_count == 1 and confidence is not None and confidence < 0.50:
        return True
    return False


def is_unreliable_speech(text: str, confidence: float | None, call_log) -> bool:
    return (
        is_truncated_speech(text, confidence)
        or is_low_confidence_speech(text, confidence)
        or needs_context_retry(text, confidence, call_log)
    )


def _noise_hint() -> str:
    return "Sorry, it's a bit noisy. After the tone, speak clearly."


def empty_gather_prompt(call_log) -> str:
    """Context-aware retry when Telnyx returns no speech."""
    history = call_log.conversation_history or []
    has_user_turn = any(h.get("role") == "user" for h in history)

    if not has_user_turn:
        return (
            f"{_noise_hint()} "
            "Tell me what's wrong — for example a kitchen leak or blocked drain."
        )

    question = _last_assistant_question(call_log)
    if question:
        if _NAME_Q.search(question):
            return (
                f"{_noise_hint()} "
                "Please say your first and last name clearly."
            )
        if _ADDRESS_Q.search(question):
            return (
                f"{_noise_hint()} "
                "Please say the house number, street name, city, state, and ZIP code clearly."
            )
        if _PROBLEM_Q.search(question):
            return (
                f"{_noise_hint()} "
                "Please tell me what plumbing issue you need help with."
            )

    return f"{_noise_hint()} Sorry, I didn't hear you. Please try again after the tone."


def truncated_gather_prompt(call_log) -> str:
    """Retry when STT only captured a fragment of the caller's sentence."""
    question = _last_assistant_question(call_log)
    if question:
        if _NAME_Q.search(question):
            return (
                f"{_noise_hint()} "
                "I only caught part of your name. Please say your full first and last name."
            )
        if _ADDRESS_Q.search(question):
            return (
                f"{_noise_hint()} "
                "I only caught part of the address. Please say the full street address, "
                "city, state, and ZIP in one sentence."
            )
        if _PROBLEM_Q.search(question):
            return (
                f"{_noise_hint()} "
                "I only caught part of that. Please tell me the full plumbing problem."
            )
    return (
        f"{_noise_hint()} "
        "I only caught part of that. After the tone, please say the full sentence again."
    )


def low_confidence_gather_prompt(call_log) -> str:
    """Retry when Telnyx confidence is too low to trust the transcript."""
    return truncated_gather_prompt(call_log)
