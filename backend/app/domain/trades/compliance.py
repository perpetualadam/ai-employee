"""Country-specific regulatory notes layered onto trade templates."""

from app.models.enums import Industry

# Region codes align with domain.telecom.resolve_region_code (US, GB, EU, AU, ...).
_COMPLIANCE: dict[tuple[str, str], str] = {
    ("US", "plumbing"): (
        "US plumbing: escalate active burst pipes, major flooding, or sewage backflow immediately. "
        "If they smell gas near plumbing appliances, treat as a gas emergency — advise leaving and calling 911."
    ),
    ("GB", "plumbing"): (
        "UK Water Fittings Regulations: plumbing must comply with local water bylaws. "
        "Escalate major flooding or sewage backflow."
    ),
    ("CA", "plumbing"): (
        "Canada: escalate burst pipes, major flooding, or sewage backup. "
        "Gas smell near water heaters — leave and call 911 or the gas utility emergency line."
    ),
    ("AU", "plumbing"): (
        "Australia: escalate major flooding or sewage overflow. Licensed plumbers required for regulated work."
    ),
    ("EU", "plumbing"): (
        "EU: cross-connection and backflow rules vary by member state — collect full address for dispatch."
    ),
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
    ("US", "hvac"): (
        "US HVAC: escalate refrigerant leaks, carbon monoxide symptoms, or no heat in freezing conditions for vulnerable occupants."
    ),
    ("GB", "hvac"): (
        "UK: Gas Safe applies when HVAC involves gas boilers. Escalate CO alarms or boiler lockouts with vulnerable occupants."
    ),
    ("AU", "hvac"): (
        "Australia: escalate CO symptoms, refrigerant leaks, or no cooling/heating for vulnerable occupants in extreme weather."
    ),
    ("US", "roofing"): (
        "US: escalate active interior flooding from roof failure during storms or structural collapse risk."
    ),
    ("GB", "roofing"): (
        "UK: escalate structural collapse risk or storm damage with active water ingress to living spaces."
    ),
    ("AU", "roofing"): (
        "Australia: escalate active ceiling collapse risk or storm ingress into occupied rooms."
    ),
    ("US", "pest_control"): (
        "US: escalate aggressive stinging insect swarms near entry points or known severe allergic occupants if mentioned."
    ),
    ("GB", "pest_control"): (
        "UK: priority when wasp/hornet nests block entry or an allergic occupant is present. "
        "Do not advise disturbing active nests."
    ),
    ("AU", "pest_control"): (
        "Australia: priority for venomous pests near living areas or allergic occupants."
    ),
    ("GB", "locksmith"): (
        "UK: verify caller authorization for property access; escalate lockouts with children or pets trapped inside."
    ),
    ("US", "locksmith"): (
        "US: verify the caller is authorised for the property; escalate when a child or pet is locked inside a vehicle or home."
    ),
    ("AU", "locksmith"): (
        "Australia: verify property access rights; escalate child/pet lock-in situations immediately."
    ),
    ("GB", "mobile_mechanic"): (
        "UK: mobile mechanics must hold valid MOT/test credentials where applicable; "
        "do not advise driving a clearly unsafe vehicle — recommend recovery instead."
    ),
    ("US", "mobile_mechanic"): (
        "US: if the vehicle is not safe to drive (no brakes, overheating, fluid leak under pressure), "
        "recommend tow/recovery rather than mobile repair on-site. Escalate motorway hard-shoulder breakdowns."
    ),
    ("AU", "mobile_mechanic"): (
        "Australia: advise against driving an unroadworthy vehicle; offer mobile call-out or tow coordination."
    ),
    ("GB", "plasterer"): (
        "UK: escalate bulging or collapsing ceilings — keep occupants away from the area."
    ),
    ("US", "plasterer"): (
        "US: escalate ceiling collapse risk or heavy debris falling — safety first."
    ),
    ("GB", "carpenter"): (
        "UK: priority when external doors cannot be secured; verify scope before quoting structural repairs."
    ),
    ("US", "carpenter"): (
        "US: priority when the property cannot be secured (broken entry door/lock). Escalate structural collapse risk."
    ),
    ("US", "landscaping"): (
        "US: priority when a fallen tree blocks driveway access or poses immediate hazard to people or structures."
    ),
    ("GB", "landscaping"): (
        "UK: priority when fallen trees block vehicle access or threaten structures."
    ),
    ("US", "appliance_repair"): (
        "US: escalate gas smell from any appliance — leave the area and call 911 or the gas utility emergency line."
    ),
    ("GB", "appliance_repair"): (
        "UK: gas cooker/oven faults may require Gas Safe engineers. Escalate gas smell — National Gas Emergency 0800 111 999."
    ),
    ("AU", "appliance_repair"): (
        "Australia: escalate gas smells from appliances; licensed gas fitters required for gas appliance work."
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
