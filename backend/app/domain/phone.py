"""Phone number normalization for CRM and voice."""


def normalize_phone(phone: str) -> str:
    """Strip to digits and leading + for comparison."""
    cleaned = phone.strip()
    digits = "".join(c for c in cleaned if c.isdigit())
    if cleaned.startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return cleaned


def is_plausible_phone(phone: str) -> bool:
    """True if the string looks like a real phone number (not garbled STT)."""
    digits = "".join(c for c in phone if c.isdigit())
    return len(digits) >= 10


def resolve_caller_phone(stt_phone: str | None, caller_id: str | None) -> str | None:
    """Prefer caller ID when STT phone is missing or too short."""
    if caller_id and caller_id not in ("text-chat", "unknown", ""):
        normalized_caller = normalize_phone(caller_id)
        if is_plausible_phone(normalized_caller):
            if not stt_phone or not is_plausible_phone(stt_phone):
                return normalized_caller
    if stt_phone and is_plausible_phone(stt_phone):
        return normalize_phone(stt_phone)
    return normalize_phone(stt_phone) if stt_phone else None
