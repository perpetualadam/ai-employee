"""Phone number normalization for CRM and voice."""

from app.domain.telecom import get_dial_code, get_telecom_profile, normalize_country_code


def normalize_phone(phone: str, country: str | None = "US") -> str:
    """Strip to E.164-style +digits using the business country when no + prefix."""
    cleaned = phone.strip()
    digits = "".join(c for c in cleaned if c.isdigit())
    if cleaned.startswith("+"):
        return f"+{digits}"

    country_code = normalize_country_code(country)
    dial = get_dial_code(country_code)

    if country_code in ("US", "CA"):
        if len(digits) == 10:
            return f"+{dial}{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"

    if digits.startswith(dial) and len(digits) > len(dial):
        return f"+{digits}"

    profile = get_telecom_profile(country_code)
    if profile.min_national_digits <= len(digits) <= profile.max_national_digits:
        return f"+{dial}{digits}"

    return cleaned


def is_plausible_phone(phone: str, country: str | None = "US") -> bool:
    """True if the string looks like a real phone number (not garbled STT)."""
    normalized = normalize_phone(phone, country)
    digits = "".join(c for c in normalized if c.isdigit())
    if not digits:
        return False

    if normalized.startswith("+"):
        if len(digits) < 10 or len(digits) > 15:
            return False
        country_code = normalize_country_code(country)
        dial = get_dial_code(country_code)
        if digits.startswith(dial):
            profile = get_telecom_profile(country_code)
            national = digits[len(dial) :]
            return profile.min_national_digits <= len(national) <= profile.max_national_digits
        return True

    country_code = normalize_country_code(country)
    profile = get_telecom_profile(country_code)
    return profile.min_national_digits <= len(digits) <= profile.max_national_digits


def resolve_caller_phone(
    stt_phone: str | None,
    caller_id: str | None,
    country: str | None = "US",
) -> str | None:
    """Prefer caller ID when STT phone is missing or too short."""
    if caller_id and caller_id not in ("text-chat", "unknown", ""):
        normalized_caller = normalize_phone(caller_id, country)
        if is_plausible_phone(normalized_caller, country):
            if not stt_phone or not is_plausible_phone(stt_phone, country):
                return normalized_caller
    if stt_phone and is_plausible_phone(stt_phone, country):
        return normalize_phone(stt_phone, country)
    return normalize_phone(stt_phone, country) if stt_phone else None
