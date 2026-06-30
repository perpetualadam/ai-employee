"""Farewell and closing detection for voice calls."""

import re

_FAREWELL = re.compile(
    r"\b("
    r"bye|goodbye|good bye|hang up|that's all|that is all|nothing else|"
    r"no further questions|no further concerns|have a good"
    r")\b",
    re.I,
)
_THANKS_BYE = re.compile(r"\b(thank you|thanks)\b.*\b(bye|goodbye|that's all)\b", re.I)
_CLOSING = re.compile(
    r"^(no|nope|no thanks|no thank you|that's fine|that's good|"
    r"i'm good|i am good|all good|nothing else|no concerns)\.?$",
    re.I,
)


def is_farewell(text: str) -> bool:
    cleaned = text.strip().strip(".")
    if not cleaned:
        return False
    return bool(_FAREWELL.search(cleaned) or _THANKS_BYE.search(cleaned))


def is_closing_acknowledgment(text: str) -> bool:
    cleaned = text.strip().strip(".")
    if not cleaned:
        return False
    return bool(_CLOSING.match(cleaned))
