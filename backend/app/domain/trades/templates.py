"""Trade template definitions — services, emergencies, and prompt fragments per industry."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import EmergencyAction, Industry
from app.schemas import BusinessServiceCreate, EmergencyRuleCreate


@dataclass(frozen=True)
class ServiceTemplate:
    name: str
    description: str
    duration_minutes: int = 60
    is_emergency: bool = False


@dataclass(frozen=True)
class EmergencyRuleTemplate:
    name: str
    keywords: tuple[str, ...]
    action: EmergencyAction
    instructions: str


@dataclass(frozen=True)
class TradeTemplate:
    industry: Industry
    label: str
    services: tuple[ServiceTemplate, ...]
    emergency_rules: tuple[EmergencyRuleTemplate, ...]
    problem_examples: str
    problem_examples_voice: str
    default_service_fallback: str
    emergency_fallback: str
    voice_greeting_example: str
    voice_empty_gather_example: str
    garbled_name_keywords: frozenset[str] = field(default_factory=frozenset)
    emergency_keywords: frozenset[str] = field(default_factory=frozenset)
    service_inference_keywords: frozenset[str] = field(default_factory=frozenset)
    tool_match_hint: str = ""
    stt_mishear_note: str = ""
    sample_service_name: str = "General service call"
    intake_questions: tuple[str, ...] = field(default_factory=tuple)

    def service_creates(self) -> list[BusinessServiceCreate]:
        return [
            BusinessServiceCreate(
                name=s.name,
                description=s.description,
                duration_minutes=s.duration_minutes,
                is_emergency=s.is_emergency,
            )
            for s in self.services
        ]

    def rule_creates(self) -> list[EmergencyRuleCreate]:
        return [
            EmergencyRuleCreate(
                name=r.name,
                keywords=list(r.keywords),
                action=r.action,
                instructions=r.instructions,
            )
            for r in self.emergency_rules
        ]


def _tpl(
    industry: Industry,
    label: str,
    services: tuple[ServiceTemplate, ...],
    rules: tuple[EmergencyRuleTemplate, ...],
    *,
    problems: str,
    problems_voice: str,
    fallback_service: str,
    fallback_emergency: str,
    voice_greeting: str,
    voice_empty: str,
    garbled: frozenset[str] = frozenset(),
    emergency_kw: frozenset[str] = frozenset(),
    inference_kw: frozenset[str] = frozenset(),
    tool_match: str = "",
    stt_note: str = "",
    sample: str = "General service call",
    intake_questions: tuple[str, ...] = (),
) -> TradeTemplate:
    return TradeTemplate(
        industry=industry,
        label=label,
        services=services,
        emergency_rules=rules,
        problem_examples=problems,
        problem_examples_voice=problems_voice,
        default_service_fallback=fallback_service,
        emergency_fallback=fallback_emergency,
        voice_greeting_example=voice_greeting,
        voice_empty_gather_example=voice_empty,
        garbled_name_keywords=garbled,
        emergency_keywords=emergency_kw,
        service_inference_keywords=inference_kw,
        tool_match_hint=tool_match,
        stt_mishear_note=stt_note,
        sample_service_name=sample,
        intake_questions=intake_questions,
    )


TRADE_TEMPLATES: dict[Industry, TradeTemplate] = {
    Industry.PLUMBING: _tpl(
        Industry.PLUMBING,
        "Plumbing",
        (
            ServiceTemplate("Drain cleaning", "Clear clogged drains and pipes", 60),
            ServiceTemplate("Water heater repair", "Diagnose and repair water heater issues", 90),
            ServiceTemplate("Emergency leak repair", "Urgent burst pipe or active leak", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "Burst pipe / flooding",
                ("burst", "flood", "water everywhere", "pipe broke", "sewage"),
                EmergencyAction.ESCALATE,
                "Treat as emergency. Collect address immediately and transfer to owner.",
            ),
            EmergencyRuleTemplate(
                "Gas smell near plumbing",
                ("gas smell", "gas leak", "smell gas"),
                EmergencyAction.ESCALATE,
                "Tell caller to leave the building and call emergency services. Transfer to owner.",
            ),
        ),
        problems="e.g. no hot water, leak, clogged drain",
        problems_voice="e.g. leak, clogged drain, no hot water",
        fallback_service="- General plumbing service (60 min)",
        fallback_emergency="- Burst pipe, flooding, gas smell → escalate immediately",
        voice_greeting="for example a leak, a clogged drain, or no hot water",
        voice_empty="a kitchen leak or blocked drain",
        garbled=frozenset({"plumbing", "drain", "pipe", "faucet", "hot water", "no hot"}),
        emergency_kw=frozenset({"flooding", "gas smell", "burst", "sewage"}),
        inference_kw=frozenset({"leak", "hot water", "drain", "pipe", "clog", "faucet"}),
        tool_match="Match service_type to what the caller described (e.g. kitchen leak → leak repair, not drain cleaning unless they said drain).",
        stt_note='Speech recognition may mis-hear "leak" as "week". If the caller says "my name is having a week/leak", treat it as a misheard problem — ask what they need fixed.',
        sample="Drain cleaning",
        intake_questions=(
            "If active leak or flooding: ask whether water is still flowing and if they can reach the main shut-off valve.",
            "If no hot water: ask whether it affects the whole property or one tap/shower.",
            "If clogged drain: ask whether water is backing up into sinks, tubs, or toilets.",
        ),
    ),
    Industry.GAS_ENGINEER: _tpl(
        Industry.GAS_ENGINEER,
        "Gas engineer / heating",
        (
            ServiceTemplate("Boiler service", "Annual boiler service and safety check", 90),
            ServiceTemplate("Gas appliance repair", "Repair cookers, fires, and gas boilers", 90),
            ServiceTemplate("Gas leak emergency", "Urgent gas leak or CO concern", 60, True),
            ServiceTemplate("Landlord gas safety certificate", "CP12 / gas safety inspection", 120),
        ),
        (
            EmergencyRuleTemplate(
                "Gas leak or CO alarm",
                ("gas leak", "smell gas", "carbon monoxide", "co alarm", "headache", "nausea"),
                EmergencyAction.ESCALATE,
                "Tell caller to leave immediately, not operate switches, and call the gas emergency line.",
            ),
            EmergencyRuleTemplate(
                "No heating — vulnerable occupant",
                ("no heating", "freezing", "elderly", "baby", "vulnerable"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority booking when heating is out in cold weather for vulnerable occupants.",
            ),
        ),
        problems="e.g. boiler not working, gas cooker fault, annual service",
        problems_voice="e.g. boiler breakdown, gas smell, no heating",
        fallback_service="- General gas / heating service (90 min)",
        fallback_emergency="- Gas leak, CO alarm, smell of gas → escalate immediately",
        voice_greeting="for example no heating, a boiler fault, or a gas appliance problem",
        voice_empty="no heating or a boiler that will not start",
        garbled=frozenset({"boiler", "gas", "heating", "carbon monoxide", "pilot light"}),
        emergency_kw=frozenset({"gas leak", "smell gas", "carbon monoxide", "co alarm"}),
        inference_kw=frozenset({"boiler", "gas", "heating", "pilot", "radiator", "cp12"}),
        tool_match="Match service_type to the appliance or issue (boiler, cooker, fire) the caller describes.",
        stt_note="If STT puts a heating or gas problem in the name field, ask what appliance or symptom they need help with.",
        sample="Boiler service",
        intake_questions=(
            "If no heating: ask whether the boiler shows an error code, low pressure, or pilot-light issue.",
            "If gas appliance fault: ask which appliance (boiler, cooker, fire) and the symptom.",
            "If they mention gas smell or a CO alarm: stop routine booking — escalate immediately per emergency rules.",
        ),
    ),
    Industry.MOBILE_MECHANIC: _tpl(
        Industry.MOBILE_MECHANIC,
        "Mobile mechanic",
        (
            ServiceTemplate("Roadside call-out", "Mobile mechanic visit — diagnostics and minor repairs", 90),
            ServiceTemplate("Battery replacement", "Test and replace battery on-site", 45),
            ServiceTemplate("Breakdown recovery assist", "On-site assessment when vehicle will not start", 60),
            ServiceTemplate("Emergency breakdown", "Stranded vehicle — safety priority", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "Stranded in unsafe location",
                ("motorway", "highway", "hard shoulder", "stranded", "not safe"),
                EmergencyAction.ESCALATE,
                "Collect exact location and transfer to owner for urgent dispatch.",
            ),
            EmergencyRuleTemplate(
                "No brakes / unsafe to drive",
                ("no brakes", "brake failure", "unsafe to drive"),
                EmergencyAction.ESCALATE,
                "Advise do not drive; arrange recovery. Escalate to owner.",
            ),
        ),
        problems="e.g. car won't start, flat battery, warning light",
        problems_voice="e.g. won't start, flat battery, strange noise",
        fallback_service="- Mobile mechanic call-out (90 min)",
        fallback_emergency="- Stranded on motorway or brake failure → escalate immediately",
        voice_greeting="for example a car that will not start, a flat battery, or a warning light",
        voice_empty="a car that will not start or a flat battery",
        garbled=frozenset({"battery", "brake", "engine", "motor", "breakdown", "stranded"}),
        emergency_kw=frozenset({"stranded", "motorway", "hard shoulder", "no brakes", "brake failure"}),
        inference_kw=frozenset({"battery", "brake", "engine", "start", "breakdown", "tow", "oil"}),
        tool_match="Match service_type to the vehicle symptom (battery, no-start, brakes) the caller describes.",
        stt_note='STT may mis-hear "brake" as "break" — clarify vehicle safety symptoms before booking.',
        sample="Roadside call-out",
        intake_questions=(
            "Ask the vehicle make/model and where it is parked (address or landmark).",
            "Ask whether the vehicle is in a safe location — motorway hard shoulder is an emergency.",
            "If won't start: ask whether they hear a click, the engine cranking, or nothing at all.",
        ),
    ),
    Industry.PLASTERER: _tpl(
        Industry.PLASTERER,
        "Plasterer / drylining",
        (
            ServiceTemplate("Patch repair", "Small hole and crack repairs", 60),
            ServiceTemplate("Room skim / replaster", "Skim coat or replaster a room", 240),
            ServiceTemplate("Water damage replaster", "Plaster repair after leak damage", 180),
        ),
        (
            EmergencyRuleTemplate(
                "Ceiling collapse risk",
                ("ceiling falling", "bulging ceiling", "collapse", "debris"),
                EmergencyAction.ESCALATE,
                "Treat as safety emergency. Collect address and escalate.",
            ),
        ),
        problems="e.g. cracked wall, hole in ceiling, skim coat needed",
        problems_voice="e.g. hole in the wall, cracked ceiling, replaster a room",
        fallback_service="- General plastering job (60 min)",
        fallback_emergency="- Ceiling collapse risk → escalate immediately",
        voice_greeting="for example a hole in the wall, a cracked ceiling, or replastering work",
        voice_empty="a hole in the wall or damage that needs replastering",
        garbled=frozenset({"plaster", "skim", "drywall", "ceiling", "crack"}),
        emergency_kw=frozenset({"ceiling falling", "collapse", "bulging ceiling"}),
        inference_kw=frozenset({"plaster", "skim", "ceiling", "wall", "crack", "hole"}),
        sample="Patch repair",
        intake_questions=(
            "Ask which room or wall is affected and roughly how large the damaged area is.",
            "If ceiling damage: ask whether the ceiling is bulging, cracking, or dropping — escalate if collapse risk.",
            "If after a leak: ask whether the area is still damp or mouldy.",
        ),
    ),
    Industry.ELECTRICAL: _tpl(
        Industry.ELECTRICAL,
        "Electrician",
        (
            ServiceTemplate("Fault finding", "Diagnose electrical faults", 90),
            ServiceTemplate("Socket / switch install", "Install or replace outlets and switches", 60),
            ServiceTemplate("Emergency power loss", "Urgent loss of power or sparking", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "Sparking / burning smell",
                ("sparking", "burning smell", "smoke", "buzzing panel"),
                EmergencyAction.ESCALATE,
                "Advise turn off affected circuit if safe. Escalate immediately.",
            ),
            EmergencyRuleTemplate(
                "Power outage — medical equipment",
                ("medical equipment", "oxygen", "power out"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority when power loss affects medical equipment.",
            ),
        ),
        problems="e.g. tripping breaker, dead socket, install light fitting",
        problems_voice="e.g. no power, tripping breaker, sparking outlet",
        fallback_service="- General electrical service (90 min)",
        fallback_emergency="- Sparking, burning smell, or shock → escalate immediately",
        voice_greeting="for example no power, a tripping breaker, or a faulty outlet",
        voice_empty="no power or a tripping breaker",
        garbled=frozenset({"electrical", "breaker", "socket", "outlet", "wiring", "spark"}),
        emergency_kw=frozenset({"sparking", "burning smell", "shock", "smoke"}),
        inference_kw=frozenset({"power", "breaker", "socket", "outlet", "light", "wiring"}),
        sample="Fault finding",
        intake_questions=(
            "If no power: ask whether it is the whole property or one room/circuit.",
            "If tripping breaker: ask what was running when it tripped (appliance, outlet, storm).",
            "If sparking, burning smell, or shock: escalate immediately — do not troubleshoot live faults.",
        ),
    ),
    Industry.HVAC: _tpl(
        Industry.HVAC,
        "HVAC / air conditioning",
        (
            ServiceTemplate("AC service", "Air conditioning service and tune-up", 90),
            ServiceTemplate("No cooling / no heat", "Diagnose heating or cooling failure", 90),
            ServiceTemplate("Emergency HVAC", "No heat in extreme cold or no cooling for vulnerable occupants", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "No heat — extreme cold",
                ("no heat", "freezing", "pipes freezing", "extreme cold"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority booking when heating fails in freezing conditions.",
            ),
            EmergencyRuleTemplate(
                "Refrigerant leak / burning smell",
                ("refrigerant", "burning smell", "smoke from unit"),
                EmergencyAction.ESCALATE,
                "Escalate and advise turning system off.",
            ),
        ),
        problems="e.g. AC not cooling, furnace not heating, thermostat issue",
        problems_voice="e.g. air conditioning not cooling, furnace not heating",
        fallback_service="- General HVAC service (90 min)",
        fallback_emergency="- No heat in freezing weather or burning smell from unit → escalate",
        voice_greeting="for example air conditioning not cooling or the furnace not heating",
        voice_empty="air conditioning not working or no heat",
        garbled=frozenset({"hvac", "furnace", "air conditioning", "thermostat", "cooling", "heating"}),
        emergency_kw=frozenset({"no heat", "freezing", "burning smell", "smoke"}),
        inference_kw=frozenset({"ac", "hvac", "heat", "cooling", "furnace", "thermostat"}),
        sample="AC service",
        intake_questions=(
            "Ask whether the issue is heating, cooling, or both.",
            "If no heat in cold weather: ask if vulnerable people (elderly, infants) are in the property.",
            "If burning smell or smoke from the unit: escalate immediately and tell them to turn the system off.",
        ),
    ),
    Industry.ROOFING: _tpl(
        Industry.ROOFING,
        "Roofing",
        (
            ServiceTemplate("Roof inspection", "Inspect roof and identify issues", 60),
            ServiceTemplate("Leak repair", "Repair active roof leak", 120),
            ServiceTemplate("Storm damage emergency", "Urgent storm damage with active ingress", 120, True),
        ),
        (
            EmergencyRuleTemplate(
                "Active flooding from roof",
                ("water coming in", "flooding", "storm damage", "hole in roof"),
                EmergencyAction.ESCALATE,
                "Collect address and escalate for emergency tarp or repair.",
            ),
        ),
        problems="e.g. missing shingles, leak in attic, storm damage",
        problems_voice="e.g. roof leak, storm damage, missing tiles",
        fallback_service="- General roofing service (60 min)",
        fallback_emergency="- Active water ingress from roof → escalate immediately",
        voice_greeting="for example a roof leak, storm damage, or missing shingles",
        voice_empty="a roof leak or storm damage",
        garbled=frozenset({"roof", "shingle", "tile", "gutter", "leak"}),
        emergency_kw=frozenset({"water coming in", "storm damage", "hole in roof"}),
        inference_kw=frozenset({"roof", "leak", "shingle", "tile", "gutter", "storm"}),
        sample="Leak repair",
        intake_questions=(
            "Ask whether water is actively coming inside right now.",
            "If storm damage: ask if the roof is exposed, tiles missing, or debris blocking access.",
            "Ask which floor/room is affected and whether a bucket or tarp is helping temporarily.",
        ),
    ),
    Industry.CARPENTER: _tpl(
        Industry.CARPENTER,
        "Carpenter / joiner",
        (
            ServiceTemplate("Door repair", "Adjust or repair doors and frames", 60),
            ServiceTemplate("Custom shelving / trim", "Install shelves, trim, or cabinetry", 120),
            ServiceTemplate("Structural wood repair", "Repair damaged framing or decking", 180),
        ),
        (
            EmergencyRuleTemplate(
                "Door won't secure — safety",
                ("can't lock", "won't close", "broken lock", "security"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority when property cannot be secured.",
            ),
        ),
        problems="e.g. sticking door, broken frame, new shelving",
        problems_voice="e.g. door that won't close, broken frame, shelving install",
        fallback_service="- General carpentry job (60 min)",
        fallback_emergency="- Property cannot be secured → priority booking",
        voice_greeting="for example a door that will not close or shelving that needs fitting",
        voice_empty="a door repair or carpentry job",
        garbled=frozenset({"door", "frame", "cabinet", "shelf", "wood"}),
        emergency_kw=frozenset({"can't lock", "won't close", "broken lock", "security"}),
        inference_kw=frozenset({"door", "frame", "cabinet", "shelf", "trim", "deck"}),
        sample="Door repair",
        intake_questions=(
            "Ask what needs repairing or installing (door, frame, shelving, trim, decking).",
            "If door won't lock or close: ask whether the property can be secured tonight.",
            "If structural wood damage: ask whether it affects load-bearing areas or safety.",
        ),
    ),
    Industry.LOCKSMITH: _tpl(
        Industry.LOCKSMITH,
        "Locksmith",
        (
            ServiceTemplate("Lockout service", "Help when locked out of home or vehicle", 45),
            ServiceTemplate("Lock change", "Replace or rekey locks", 60),
            ServiceTemplate("Emergency lockout", "Urgent lockout with safety concern", 45, True),
        ),
        (
            EmergencyRuleTemplate(
                "Child or pet locked inside",
                ("child locked", "baby inside", "pet locked", "locked in"),
                EmergencyAction.ESCALATE,
                "Escalate immediately for urgent lockout.",
            ),
        ),
        problems="e.g. locked out, broken key, need new locks",
        problems_voice="e.g. locked out, key snapped, need locks changed",
        fallback_service="- Locksmith call-out (45 min)",
        fallback_emergency="- Child or pet locked inside → escalate immediately",
        voice_greeting="for example being locked out, a broken key, or needing locks changed",
        voice_empty="being locked out or a broken key",
        garbled=frozenset({"locked", "lockout", "key", "lock"}),
        emergency_kw=frozenset({"child locked", "baby inside", "pet locked"}),
        inference_kw=frozenset({"lock", "key", "lockout", "deadbolt"}),
        sample="Lockout service",
        intake_questions=(
            "Ask whether they are locked out of a home, vehicle, or commercial property.",
            "Ask if they have ID or proof they are authorised to access the property.",
            "If a child or pet is locked inside: escalate immediately per emergency rules.",
        ),
    ),
    Industry.PEST_CONTROL: _tpl(
        Industry.PEST_CONTROL,
        "Pest control",
        (
            ServiceTemplate("General pest treatment", "Inspection and treatment for common pests", 90),
            ServiceTemplate("Rodent control", "Rodent inspection and baiting", 90),
            ServiceTemplate("Wasp / hornet emergency", "Active nest near entry — urgent", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "Aggressive wasp / hornet nest",
                ("wasp", "hornet", "nest", "stung", "allergic"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority when nest is near entry or allergic occupant mentioned.",
            ),
        ),
        problems="e.g. ants, mice, wasps, bed bugs",
        problems_voice="e.g. mice, wasps, ants, bed bugs",
        fallback_service="- General pest inspection (90 min)",
        fallback_emergency="- Wasps near entry or allergic reaction risk → priority",
        voice_greeting="for example mice, wasps, ants, or other pests",
        voice_empty="a pest problem such as mice or wasps",
        garbled=frozenset({"pest", "wasp", "mouse", "rat", "bed bug", "ant"}),
        emergency_kw=frozenset({"wasp", "hornet", "allergic", "stung"}),
        inference_kw=frozenset({"pest", "wasp", "mouse", "rat", "ant", "bed bug"}),
        sample="General pest treatment",
        intake_questions=(
            "Ask what pest they've seen and where in the property (kitchen, loft, garden, etc.).",
            "If wasps/hornets: ask if the nest is near an entry door or window and if anyone has allergies.",
            "If rodents: ask whether they've seen droppings, heard scratching, or noticed gnaw marks.",
        ),
    ),
    Industry.LANDSCAPING: _tpl(
        Industry.LANDSCAPING,
        "Landscaping / gardening",
        (
            ServiceTemplate("Lawn maintenance", "Mowing, edging, and tidy-up", 90),
            ServiceTemplate("Tree trimming", "Trim branches and hedges", 120),
            ServiceTemplate("Storm debris clearance", "Urgent clearance after storm", 120, True),
        ),
        (
            EmergencyRuleTemplate(
                "Fallen tree blocking access",
                ("fallen tree", "blocking driveway", "blocked access"),
                EmergencyAction.PRIORITY_BOOK,
                "Priority when access is blocked.",
            ),
        ),
        problems="e.g. lawn care, hedge trim, garden tidy",
        problems_voice="e.g. lawn mowing, hedge trimming, fallen branch",
        fallback_service="- General landscaping visit (90 min)",
        fallback_emergency="- Fallen tree blocking access → priority",
        voice_greeting="for example lawn care, hedge trimming, or garden maintenance",
        voice_empty="lawn care or hedge trimming",
        garbled=frozenset({"lawn", "garden", "hedge", "tree", "mow"}),
        emergency_kw=frozenset({"fallen tree", "blocking driveway", "blocked access"}),
        inference_kw=frozenset({"lawn", "garden", "hedge", "tree", "mow", "landscape"}),
        sample="Lawn maintenance",
        intake_questions=(
            "Ask what outdoor work they need (lawn mowing, hedge trimming, tree work, garden tidy).",
            "If fallen tree or branch: ask whether it is blocking a driveway, road, or building access.",
            "Ask approximate garden size or number of trees if quoting a visit.",
        ),
    ),
    Industry.PAINTER: _tpl(
        Industry.PAINTER,
        "Painter / decorator",
        (
            ServiceTemplate("Interior room paint", "Paint walls and ceilings in one room", 240),
            ServiceTemplate("Exterior touch-up", "Exterior paint repair and touch-up", 180),
            ServiceTemplate("Water stain / mold prep", "Treat and prep water-damaged surfaces", 120),
        ),
        (
            EmergencyRuleTemplate(
                "Commercial deadline slip",
                ("shop opening", "deadline tomorrow", "must open"),
                EmergencyAction.MESSAGE_OWNER,
                "Message owner for rush scheduling — not a life-safety emergency.",
            ),
        ),
        problems="e.g. repaint a room, exterior peeling paint, water stains",
        problems_voice="e.g. repaint a bedroom, peeling exterior paint",
        fallback_service="- General painting estimate visit (60 min)",
        fallback_emergency="- Rush commercial deadline → message owner",
        voice_greeting="for example repainting a room or exterior touch-up work",
        voice_empty="interior or exterior painting work",
        garbled=frozenset({"paint", "wall", "ceiling", "peeling"}),
        inference_kw=frozenset({"paint", "room", "exterior", "stain", "decorator"}),
        sample="Interior room paint",
        intake_questions=(
            "Ask which rooms or exterior areas need painting and how many coats/surfaces.",
            "If water stains or mould: ask whether the leak source is fixed and if prep is needed.",
            "Rush commercial deadlines are not life-safety emergencies — use message_owner if they insist on same-day.",
        ),
    ),
    Industry.APPLIANCE_REPAIR: _tpl(
        Industry.APPLIANCE_REPAIR,
        "Appliance repair",
        (
            ServiceTemplate("Domestic appliance repair", "Washer, dryer, fridge, oven diagnostics", 90),
            ServiceTemplate("Installation hook-up", "Install and connect appliances", 60),
            ServiceTemplate("Gas appliance repair", "Gas cooker or oven repair", 90, True),
        ),
        (
            EmergencyRuleTemplate(
                "Gas appliance smell",
                ("gas smell", "smell gas", "gas leak"),
                EmergencyAction.ESCALATE,
                "Escalate gas smell — advise leaving area and calling gas emergency line.",
            ),
        ),
        problems="e.g. washing machine not draining, fridge not cooling",
        problems_voice="e.g. washing machine fault, oven not heating, fridge warm",
        fallback_service="- Appliance diagnostic visit (90 min)",
        fallback_emergency="- Gas smell from appliance → escalate immediately",
        voice_greeting="for example a washing machine fault, an oven not heating, or a fridge not cooling",
        voice_empty="an appliance that is not working properly",
        garbled=frozenset({"washer", "dryer", "fridge", "oven", "appliance"}),
        emergency_kw=frozenset({"gas smell", "smell gas"}),
        inference_kw=frozenset({"washer", "dryer", "fridge", "oven", "dishwasher", "appliance"}),
        sample="Domestic appliance repair",
        intake_questions=(
            "Ask which appliance and the symptom (not cooling, leaking, error code, not heating, etc.).",
            "Ask the brand/model if they know it — helps the technician prepare.",
            "If gas appliance smell: escalate immediately — do not continue routine booking questions.",
        ),
    ),
    Industry.GENERAL: _tpl(
        Industry.GENERAL,
        "General trades",
        (
            ServiceTemplate("General service call", "On-site assessment and quote", 60),
            ServiceTemplate("Emergency call-out", "Urgent same-day call-out", 60, True),
        ),
        (
            EmergencyRuleTemplate(
                "Safety emergency",
                ("emergency", "unsafe", "danger", "injury"),
                EmergencyAction.ESCALATE,
                "Escalate any immediate safety risk.",
            ),
        ),
        problems="e.g. repair needed, installation, maintenance issue",
        problems_voice="e.g. something broken, needs repair, maintenance visit",
        fallback_service="- General service call (60 min)",
        fallback_emergency="- Immediate safety risk → escalate",
        voice_greeting="what you need help with today",
        voice_empty="the problem you need help with",
        inference_kw=frozenset({"repair", "broken", "install", "fix", "service"}),
        sample="General service call",
        intake_questions=(
            "Ask them to describe the problem in their own words before suggesting a service.",
            "Ask whether anyone is in immediate danger or if utilities (gas, electric, water) are involved.",
            "If they mention fire, gas smell, flooding, or injury: escalate per emergency rules.",
        ),
    ),
}
