"""Country-specific regulatory notes layered onto trade templates."""

from app.models.enums import Industry

# Region codes align with domain.telecom.resolve_region_code (US, GB, EU, AU, ...).
_COMPLIANCE: dict[tuple[str, str], str] = {
    ("US", "gas_engineer"): (
        "US gas safety: escalate active gas leaks or CO alarms immediately. "
        "Advise the caller to leave the premises, avoid switches/flames, and call 911 or their gas utility emergency line."
    ),
    ("CA", "gas_engineer"): (
        "Canada: escalate gas leaks immediately. Advise the caller to leave, not operate switches, "
        "and contact their gas utility emergency number or 911."
    ),
    ("GB", "gas_engineer"): (
        "UK Gas Safe: only Gas Safe registered engineers may work on gas appliances. "
        "Do not advise DIY on gas. Escalate suspected gas leaks — tell the caller to turn off gas at the meter if safe, "
        "open windows, leave the property, and call the National Gas Emergency Service on 0800 111 999."
    ),
    ("EU", "gas_engineer"): (
        "EU: gas installation and repair must be performed by locally certified gas installers. "
        "Escalate gas leaks immediately and direct the caller to their national gas emergency number."
    ),
    ("AU", "gas_engineer"): (
        "Australia: gas work requires licensed gas fitters. Escalate gas leaks — advise leaving the area "
        "and contacting the gas distributor emergency line."
    ),
    ("US", "electrical"): (
        "US electrical: escalate downed power lines, burning smells from panels, or shock hazards. "
        "Advise staying away from energized equipment."
    ),
    ("GB", "electrical"): (
        "UK Part P: notifiable electrical work in dwellings requires qualified electricians. "
        "Escalate burning smells, sparking outlets, or exposed live conductors."
    ),
    ("EU", "electrical"): (
        "EU: electrical work must comply with local qualified-installer rules. "
        "Escalate fire, shock, or burning-smell emergencies."
    ),
    ("AU", "electrical"): (
        "Australia: electrical work requires licensed electricians. Escalate shock, fire, or storm-damage hazards."
    ),
    ("GB", "mobile_mechanic"): (
        "UK: mobile mechanics must hold valid MOT/test credentials where applicable; "
        "do not advise driving an clearly unsafe vehicle — recommend recovery instead."
    ),
    ("US", "mobile_mechanic"): (
        "US: if the vehicle is not safe to drive (no brakes, overheating, fluid leak under pressure), "
        "recommend tow/recovery rather than mobile repair on-site."
    ),
    ("AU", "mobile_mechanic"): (
        "Australia: advise against driving an unroadworthy vehicle; offer mobile call-out or tow coordination."
    ),
    ("GB", "plumbing"): (
        "UK Water Fittings Regulations: plumbing must comply with local water bylaws. "
        "Escalate major flooding or sewage backflow."
    ),
    ("EU", "plumbing"): (
        "EU: cross-connection and backflow rules vary by member state — collect full address for dispatch."
    ),
    ("US", "hvac"): (
        "US HVAC: escalate refrigerant leaks, carbon monoxide symptoms, or no heat in freezing conditions for vulnerable occupants."
    ),
    ("GB", "hvac"): (
        "UK: Gas Safe applies when HVAC involves gas boilers. Escalate CO alarms or boiler lockouts with vulnerable occupants."
    ),
    ("US", "roofing"): (
        "US: escalate active interior flooding from roof failure during storms."
    ),
    ("GB", "roofing"): (
        "UK: escalate structural collapse risk or storm damage with active water ingress to living spaces."
    ),
    ("US", "pest_control"): (
        "US: escalate aggressive stinging insect swarms near entry points or known severe allergic occupants if mentioned."
    ),
    ("GB", "locksmith"): (
        "UK: verify caller authorization for property access; escalate lockouts with children or pets trapped inside."
    ),
}


def get_compliance_notes(industry: Industry, region: str) -> str:
    """Return regulatory guidance for prompt injection; empty when none defined."""
    notes = _COMPLIANCE.get((region, industry.value), "")
    if notes:
        return notes
    # Fall back to region-only general trade note for regulated trades
    generic = _COMPLIANCE.get((region, "general"), "")
    return generic
