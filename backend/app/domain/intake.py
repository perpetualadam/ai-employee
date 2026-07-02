"""Validate caller intake fields before booking."""

import re

from app.models.enums import Industry

_PLACEHOLDER_NAME = re.compile(
    r"^(caller|customer|unknown|guest|user|test|voice|new customer|phone caller)\b",
    re.I,
)

_PLACEHOLDER_ADDRESS = re.compile(
    r"^(unknown|n/a|na|none|tbd|address|no address|not provided)\b",
    re.I,
)

_STREET_TYPE = re.compile(
    r"\b(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|way|blvd|boulevard|"
    r"circle|cir|place|pl|parkway|pkwy|highway|hwy|trail|trl|terrace|ter)\b",
    re.I,
)

_STREET_NUMBER = re.compile(r"\b\d{1,6}\b")

_ZIP_CODE = re.compile(r"\b\d{5}(?:-\d{4})?\b")

_UNIT_PREFIX = re.compile(r"\b(apt|apartment|suite|ste|unit|#)\b", re.I)

_NAME_INTRO = re.compile(
    r"(?:my name is|this is|i'?m|i am|it'?s)\s+(.+)",
    re.I,
)

_HAVING_PROBLEM = re.compile(
    r"(?:my name is|i'?m|i am|this is)\s+having\s+(?:a\s+)?(.+)",
    re.I,
)

_UNIVERSAL_GARBLED_NAME = re.compile(
    r"\b(having|leak|leaking|water|flood|flooding|clog)\b",
    re.I,
)

_GARBLED_NAME = re.compile(
    r"\b(having|leak|leaking|water|plumbing|flood|flooding|drain|clog|hot water|no hot|faucet|pipe)\b",
    re.I,
)

_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "ohio",
    "oklahoma", "oregon", "pennsylvania", "tennessee", "texas", "utah", "virginia",
    "washington", "wisconsin",
}

_US_STATE_ABBREVS = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in",
    "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv",
    "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn",
    "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
}

_STREET_TYPE_TOKENS = {
    "street", "st", "avenue", "ave", "road", "rd", "drive", "dr", "lane", "ln", "court",
    "ct", "way", "blvd", "boulevard", "circle", "cir", "place", "pl", "parkway", "pkwy",
    "highway", "hwy", "trail", "trl", "terrace", "ter",
}

US_ADDRESS_FORMAT_HINT = (
    "US service address: house number + street name + street type "
    "(+ Apt/Suite/Unit if applicable) + city + state + 5-digit ZIP code."
)


def _trade_garbled_pattern(industry: Industry | str | None) -> re.Pattern[str] | None:
    if industry is None:
        return None
    from app.domain.trades.registry import get_trade_template

    keywords = get_trade_template(industry).garbled_name_keywords
    if not keywords:
        return None
    return re.compile(
        r"\b(" + "|".join(re.escape(k) for k in sorted(keywords, key=len, reverse=True)) + r")\b",
        re.I,
    )


def is_valid_customer_name(
    name: str | None,
    industry: Industry | str | None = None,
) -> bool:
    cleaned = (name or "").strip()
    if len(cleaned) < 2:
        return False
    if _PLACEHOLDER_NAME.match(cleaned):
        return False
    if _UNIVERSAL_GARBLED_NAME.search(cleaned):
        return False
    trade_pattern = _trade_garbled_pattern(industry)
    if trade_pattern and trade_pattern.search(cleaned):
        return False
    if industry is None and _GARBLED_NAME.search(cleaned):
        return False
    return cleaned.lower() not in {
        "caller",
        "customer",
        "unknown",
        "guest",
        "user",
        "test",
    }


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _has_us_state(text: str) -> bool:
    tokens = _tokenize(text)
    return any(t in _US_STATES or t in _US_STATE_ABBREVS for t in tokens)


def _has_city(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False

    if "," in cleaned:
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        for part in parts[1:]:
            if _UNIT_PREFIX.search(part):
                continue
            letters = re.sub(r"[^a-zA-Z]", "", part)
            if len(letters) <= 2 and _has_us_state(part):
                continue
            if _ZIP_CODE.search(part) and len(letters) <= 2:
                continue
            if len(letters) >= 3:
                return True
        return False

    tokens = _tokenize(cleaned)
    state_idx = next(
        (i for i, token in enumerate(tokens) if token in _US_STATES or token in _US_STATE_ABBREVS),
        None,
    )
    if state_idx is None:
        return False

    city_tokens: list[str] = []
    for token in reversed(tokens[:state_idx]):
        if token in _STREET_TYPE_TOKENS:
            break
        if token.isdigit() and len(token) >= 5:
            continue
        if token.isdigit():
            continue
        if token in _US_STATES or token in _US_STATE_ABBREVS:
            continue
        city_tokens.append(token)

    return any(len(token) >= 3 for token in city_tokens)


def validate_us_service_address(address: str | None) -> tuple[bool, list[str]]:
    """Return whether address meets US intake rules and which parts are missing."""
    cleaned = (address or "").strip()
    missing: list[str] = []

    if len(cleaned) < 12:
        missing.append("complete address")
    if _PLACEHOLDER_ADDRESS.match(cleaned):
        missing.append("real address (not a placeholder)")
    if not _STREET_NUMBER.search(cleaned):
        missing.append("house/building number")
    if not _STREET_TYPE.search(cleaned):
        missing.append("street type (Street, Avenue, Way, Boulevard, etc.)")
    if not _has_city(cleaned):
        missing.append("city")
    if not _has_us_state(cleaned):
        missing.append("state")
    if not _ZIP_CODE.search(cleaned):
        missing.append("5-digit ZIP code")

    return (len(missing) == 0, missing)


def service_address_validation_message(address: str | None) -> str:
    ok, missing = validate_us_service_address(address)
    if ok:
        return ""
    return f"{US_ADDRESS_FORMAT_HINT} Still needed: {', '.join(missing)}."


def is_valid_service_address(address: str | None) -> bool:
    ok, _ = validate_us_service_address(address)
    return ok


def _normalize_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for part in re.findall(r"[a-z0-9]+", text.lower()):
        if part.isdigit() or len(part) > 1:
            tokens.add(part)
    return tokens


def address_appears_in_caller_text(address: str, caller_messages: list[str]) -> bool:
    """True when the address uses words/numbers the caller actually said (not model-only)."""
    if not address or not caller_messages:
        return False
    addr_tokens = _normalize_tokens(address)
    caller_tokens = _normalize_tokens(" ".join(caller_messages))
    if not addr_tokens:
        return False
    street_numbers = {t for t in addr_tokens if t.isdigit() and len(t) >= 2}
    if street_numbers and not street_numbers <= caller_tokens:
        return False
    overlap = addr_tokens & caller_tokens
    min_overlap = 3 if len(addr_tokens) >= 4 else 2
    return len(overlap) >= min_overlap


def extract_spoken_name(text: str, industry: Industry | str | None = None) -> str | None:
    """Pull a name from phrases like 'my name is John Doe'."""
    if _HAVING_PROBLEM.search(text.strip()):
        return None
    match = _NAME_INTRO.search(text.strip())
    if not match:
        return None
    name = match.group(1).strip().strip(".")
    return name if is_valid_customer_name(name, industry=industry) else None


def normalize_caller_speech(text: str, industry: Industry | str | None = None) -> str:
    """Normalize common STT phrasing so the agent receives clear intake."""
    cleaned = text.strip()
    having = _HAVING_PROBLEM.search(cleaned)
    if having:
        rest = having.group(1).strip().strip(".")
        if re.search(r"\bweek\b", rest, re.I):
            return "I have a leak"
        if re.search(r"\bleak", rest, re.I):
            return "I have a water leak"
        return f"I have a problem with {rest}"

    # Common Telnyx mis-hear without "my name is" prefix.
    if re.search(r"\bi'?m having a week\b", cleaned, re.I):
        return "I have a leak"
    if re.search(r"\bi'?m having a (?:water )?leak\b", cleaned, re.I):
        return "I have a water leak"
    name = extract_spoken_name(cleaned, industry=industry)
    if name:
        return f"My name is {name}"
    return cleaned
