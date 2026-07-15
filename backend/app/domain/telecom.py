"""Country telecom profiles — phone rules, address hints, and provider recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.intake import US_ADDRESS_FORMAT_HINT

# EU member states — share EU operational profile; dial codes remain per country.
EU_MEMBER_CODES = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
)

COUNTRY_DIAL_CODES: dict[str, str] = {
    "US": "1",
    "CA": "1",
    "AU": "61",
    "GB": "44",
    "NZ": "64",

    "DE": "49",
    "FR": "33",
    "IT": "39",
    "ES": "34",
    "NL": "31",
    "BE": "32",
    "AT": "43",
    "IE": "353",
    "PT": "351",
    "SE": "46",
    "DK": "45",
    "FI": "358",
    "PL": "48",
    "CZ": "420",
    "RO": "40",
    "HU": "36",
    "GR": "30",
}

ADDRESS_FORMAT_HINTS: dict[str, str] = {
    "US": US_ADDRESS_FORMAT_HINT,
    "CA": (
        "Canadian service address: civic number + street name, city, province "
        "(e.g. ON, BC), and postal code (e.g. K1A 0B1)."
    ),
    "AU": (
        "Australian service address: street number and name, suburb, state "
        "(e.g. NSW, VIC), and 4-digit postcode."
    ),
    "GB": (
        "UK service address: house number and street, town/city, and postcode "
        "(e.g. SW1A 1AA)."
    ),
    "NZ": (
        "New Zealand service address: street number and name, suburb, city, "
        "and 4-digit postcode."
    ),
    "EU": (
        "European service address: street and number, city, postal code, and country."
    ),

}


@dataclass(frozen=True)
class NumberSearchProfile:
    """
    How to search for purchasable numbers in a country.

    Attributes
    ----------
    prefix_param:
        The Telnyx API filter key used to narrow the search to a local area/region.
        ``None`` means the country doesn't support prefix filtering via Telnyx.
    prefix_label:
        Human-readable label shown in the UI (e.g. "Area code", "NDC", "STD prefix").
    prefix_digits:
        Tuple of acceptable digit lengths for the prefix.  Empty means any length
        passes (no client-side validation).
    prefix_example:
        Example prefix string shown as placeholder in the UI.
    """

    prefix_param: str | None  # Telnyx query param name, or None if not supported
    prefix_label: str
    prefix_digits: tuple[int, ...]  # valid digit counts; () = unchecked
    prefix_example: str


# Maps each region/country code to number-search parameters.
# Keys must match keys used in TELECOM_PROFILES or normalised 2-letter country codes.
NUMBER_SEARCH_PROFILES: dict[str, NumberSearchProfile] = {
    # US / Canada — 3-digit area code, Telnyx NDC filter.
    "US": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area code",
        prefix_digits=(3,),
        prefix_example="415",
    ),
    "CA": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area code",
        prefix_digits=(3,),
        prefix_example="416",
    ),
    # UK — Telnyx uses locality filter for GB numbers.
    "GB": NumberSearchProfile(
        prefix_param="filter[locality]",
        prefix_label="City / area",
        prefix_digits=(),  # free text
        prefix_example="London",
    ),
    # Australia — 2-digit STD area code.
    "AU": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="STD area code",
        prefix_digits=(2,),
        prefix_example="02",
    ),
    # New Zealand — no stable NDC filter; country-level search only.
    "NZ": NumberSearchProfile(
        prefix_param=None,
        prefix_label="Area code",
        prefix_digits=(2, 3),
        prefix_example="09",
    ),
    # EU (catch-all for member states without dedicated profile).
    "EU": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area / NDC",
        prefix_digits=(),
        prefix_example="",
    ),
    # Germany — Telnyx NDC.
    "DE": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area code (Vorwahl)",
        prefix_digits=(2, 3, 4, 5),
        prefix_example="30",
    ),
    # France.
    "FR": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area code",
        prefix_digits=(1,),
        prefix_example="1",
    ),

    # Ireland.
    "IE": NumberSearchProfile(
        prefix_param="filter[national_destination_code]",
        prefix_label="Area code",
        prefix_digits=(1, 2),
        prefix_example="1",
    ),
}


def get_number_search_profile(country: str | None) -> NumberSearchProfile:
    """
    Return the number-search profile for a country.

    Resolution order:
      1. Exact 2-letter code (e.g. ``GB``, ``DE``).
      2. EU catch-all for member states not listed above.
      3. US fallback.
    """
    code = normalize_country_code(country)
    if code in NUMBER_SEARCH_PROFILES:
        return NUMBER_SEARCH_PROFILES[code]
    if code in EU_MEMBER_CODES:
        return NUMBER_SEARCH_PROFILES["EU"]
    return NUMBER_SEARCH_PROFILES["US"]


@dataclass(frozen=True)
class TelecomProfile:
    """Operational guidance for a country/region — swap providers via env + recommendations."""

    region_code: str
    recommended_voice_providers: tuple[str, ...]
    recommended_sms_providers: tuple[str, ...]
    min_national_digits: int
    max_national_digits: int
    sms_regulatory_note: str = ""


TELECOM_PROFILES: dict[str, TelecomProfile] = {
    "US": TelecomProfile(
        region_code="US",
        recommended_voice_providers=("telnyx", "twilio"),
        recommended_sms_providers=("telnyx", "twilio"),
        min_national_digits=10,
        max_national_digits=10,
    ),
    "AU": TelecomProfile(
        region_code="AU",
        recommended_voice_providers=("telnyx", "twilio"),
        recommended_sms_providers=("telnyx", "twilio"),
        min_national_digits=9,
        max_national_digits=10,
    ),
    "GB": TelecomProfile(
        region_code="GB",
        recommended_voice_providers=("telnyx", "twilio"),
        recommended_sms_providers=("telnyx", "twilio"),
        min_national_digits=10,
        max_national_digits=11,
    ),
    "NZ": TelecomProfile(
        region_code="NZ",
        recommended_voice_providers=("telnyx", "twilio"),
        recommended_sms_providers=("telnyx", "twilio"),
        min_national_digits=8,
        max_national_digits=10,
    ),
    "EU": TelecomProfile(
        region_code="EU",
        recommended_voice_providers=("telnyx", "twilio"),
        recommended_sms_providers=("telnyx", "twilio", "messagebird"),
        min_national_digits=8,
        max_national_digits=12,
        sms_regulatory_note="Use a local sender ID or number where required by member state.",
    ),

}


def normalize_country_code(country: str | None) -> str:
    code = (country or "US").upper().strip()
    if len(code) != 2:
        return "US"
    return code


def resolve_region_code(country: str | None) -> str:
    code = normalize_country_code(country)
    if code in TELECOM_PROFILES:
        return code
    if code in EU_MEMBER_CODES:
        return "EU"
    return "US"


def get_dial_code(country: str | None) -> str:
    code = normalize_country_code(country)
    return COUNTRY_DIAL_CODES.get(code, COUNTRY_DIAL_CODES["US"])


def get_telecom_profile(country: str | None) -> TelecomProfile:
    region = resolve_region_code(country)
    return TELECOM_PROFILES.get(region, TELECOM_PROFILES["US"])


def get_address_format_hint(country: str | None) -> str:
    region = resolve_region_code(country)
    if region in ADDRESS_FORMAT_HINTS:
        return ADDRESS_FORMAT_HINTS[region]
    code = normalize_country_code(country)
    return ADDRESS_FORMAT_HINTS.get(code, US_ADDRESS_FORMAT_HINT)


def build_recovery_link_prompt_rules(*, sms_functional: bool, voice_mode: bool) -> str:
    """Prompt fragment for recovery links — SMS first when configured, web chat fallback."""
    if sms_functional and voice_mode:
        return (
            "- If speech recognition mishears the name, address, email, or anything else, "
            "call send_web_chat_link right away — it texts the link to their phone when SMS works.\n"
            "- Tell the caller: \"I've sent you a text with a link — tap it to type your name, "
            "address, email, and finish booking.\"\n"
            "- Stay on the line briefly in case the text is delayed; if needed, also read the "
            "continue link from the tool result.\n"
            "- Optional: if they already gave a clear email, pass it to send_web_chat_link "
            "so the link is emailed too.\n"
            "- Do NOT use send_address_confirmation_link unless SMS and web chat both failed.\n"
            "- NEVER send more than one recovery link per call — if already sent, remind them "
            "to check their text message or open the link you gave them."
        )
    if sms_functional and not voice_mode:
        return (
            "- If name, address, or email keeps failing validation, call send_web_chat_link — "
            "it texts the link to their phone when SMS works.\n"
            "- Tell them to check their text message and tap the link to type their details.\n"
            "- NEVER send more than one recovery link per session."
        )
    if voice_mode:
        return (
            "- If speech recognition mishears the name, address, email, or anything else, "
            "call send_web_chat_link right away — SMS is not configured, so give the link on the call.\n"
            "- Tell the caller to open the web chat link on their phone browser NOW and type "
            "their details: name, address, email, and finish booking.\n"
            "- Optional: if they already gave a clear email, pass it to send_web_chat_link "
            "so the link can be emailed too.\n"
            "- NEVER send more than one recovery link per call — if already sent, remind them "
            "to open the web chat link you gave them."
        )
    return (
        "- If name, address, or email keeps failing validation, call send_web_chat_link and "
        "tell them to open the link and type their details online (once per session only)."
    )


_COUNTRY_LABELS: dict[str, str] = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
    "AU": "Australia",
    "NZ": "New Zealand",

    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "AT": "Austria",
    "IE": "Ireland",
    "PT": "Portugal",
    "SE": "Sweden",
    "DK": "Denmark",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "RO": "Romania",
    "HU": "Hungary",
    "GR": "Greece",
}


def get_supported_countries() -> list[dict[str, str]]:
    """Countries with telecom/address profiles — for onboarding UI.

    Returns only real 2-letter ISO country codes.  Internal region tokens such
    as ``EU`` (used as a catch-all profile key) are excluded.
    """
    # COUNTRY_DIAL_CODES only has real ISO codes; ADDRESS_FORMAT_HINTS contains
    # the pseudo-key "EU" which must not appear in the onboarding dropdown.
    codes = sorted(set(COUNTRY_DIAL_CODES) | (set(ADDRESS_FORMAT_HINTS) - {"EU"}))
    return [
        {"code": code, "label": _COUNTRY_LABELS.get(code, code)}
        for code in codes
    ]
