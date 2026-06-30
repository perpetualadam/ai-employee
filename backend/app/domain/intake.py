"""Validate caller intake fields before booking."""

import re

_PLACEHOLDER_NAME = re.compile(
    r"^(caller|customer|unknown|guest|user|test|voice|new customer|phone caller)\b",
    re.I,
)

_PLACEHOLDER_ADDRESS = re.compile(
    r"^(unknown|n/a|na|none|tbd|address|no address|not provided)\b",
    re.I,
)

_HAS_STREET_DETAIL = re.compile(
    r"\d+|street|st\b|avenue|ave\b|road|rd\b|drive|dr\b|lane|ln\b|"
    r"court|ct\b|way|blvd|boulevard|apt|unit|#",
    re.I,
)

_NAME_INTRO = re.compile(
    r"(?:my name is|this is|i'?m|i am|it'?s)\s+(.+)",
    re.I,
)


def is_valid_customer_name(name: str | None) -> bool:
    cleaned = (name or "").strip()
    if len(cleaned) < 2:
        return False
    if _PLACEHOLDER_NAME.match(cleaned):
        return False
    return cleaned.lower() not in {
        "caller",
        "customer",
        "unknown",
        "guest",
        "user",
        "test",
    }


def is_valid_service_address(address: str | None) -> bool:
    cleaned = (address or "").strip()
    if len(cleaned) < 8:
        return False
    if _PLACEHOLDER_ADDRESS.match(cleaned):
        return False
    if not _HAS_STREET_DETAIL.search(cleaned):
        return False
    return True


def extract_spoken_name(text: str) -> str | None:
    """Pull a name from phrases like 'my name is John Doe'."""
    match = _NAME_INTRO.search(text.strip())
    if not match:
        return None
    name = match.group(1).strip().strip(".")
    return name if is_valid_customer_name(name) else None


def normalize_caller_speech(text: str) -> str:
    """Normalize common STT phrasing so the agent receives clear intake."""
    name = extract_spoken_name(text)
    if name:
        return f"My name is {name}"
    return text.strip()
