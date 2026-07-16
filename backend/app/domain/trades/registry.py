"""Trade template registry — shared trade definitions, compliance, and runtime context."""

from app.domain.trades.compliance import get_compliance_notes
from app.domain.trades.templates import TRADE_TEMPLATES, TradeTemplate
from app.domain.telecom import get_address_format_hint, resolve_region_code
from app.models import Business
from app.models.enums import Industry

__all__ = [
    "TradeContext",
    "TradeTemplate",
    "get_trade_template",
    "list_trade_options",
    "resolve_trade_context",
]


class TradeContext:
    """Resolved trade + country context for prompts, voice, and validation."""

    __slots__ = (
        "industry",
        "label",
        "country",
        "region",
        "problem_examples",
        "problem_examples_voice",
        "default_service_fallback",
        "emergency_fallback",
        "voice_greeting_example",
        "voice_empty_gather_example",
        "garbled_name_keywords",
        "emergency_keywords",
        "service_inference_keywords",
        "tool_match_hint",
        "stt_mishear_note",
        "sample_service_name",
        "compliance_notes",
        "address_hint",
        "intake_questions",
    )

    def __init__(self, template: TradeTemplate, business: Business) -> None:
        region = resolve_region_code(business.country)
        self.industry = template.industry
        self.label = template.label
        self.country = business.country
        self.region = region
        self.problem_examples = template.problem_examples
        self.problem_examples_voice = template.problem_examples_voice
        self.default_service_fallback = template.default_service_fallback
        self.emergency_fallback = template.emergency_fallback
        self.voice_greeting_example = template.voice_greeting_example
        self.voice_empty_gather_example = template.voice_empty_gather_example
        self.garbled_name_keywords = template.garbled_name_keywords
        self.emergency_keywords = _UNIVERSAL_EMERGENCY_KEYWORDS | template.emergency_keywords
        self.service_inference_keywords = template.service_inference_keywords
        self.tool_match_hint = template.tool_match_hint
        self.stt_mishear_note = template.stt_mishear_note
        self.sample_service_name = template.sample_service_name
        self.compliance_notes = get_compliance_notes(template.industry, region)
        self.address_hint = get_address_format_hint(business.country)
        self.intake_questions = template.intake_questions


_UNIVERSAL_EMERGENCY_KEYWORDS = frozenset(
    {"emergency", "urgent", "immediately", "asap", "right away"}
)


def get_trade_template(industry: Industry | str) -> TradeTemplate:
    key = Industry(industry) if isinstance(industry, str) else industry
    return TRADE_TEMPLATES.get(key, TRADE_TEMPLATES[Industry.GENERAL])


def resolve_trade_context(business: Business) -> TradeContext:
    return TradeContext(get_trade_template(business.industry), business)


def list_trade_options() -> list[dict]:
    """Catalog for onboarding UI — value, label, and service preview names."""
    order = [t for t in TRADE_TEMPLATES.values() if t.industry != Industry.GENERAL]
    order.append(TRADE_TEMPLATES[Industry.GENERAL])
    return [
        {
            "value": template.industry.value,
            "label": template.label,
            "services": [service.name for service in template.services],
            "emergency_rules": [rule.name for rule in template.emergency_rules],
        }
        for template in order
    ]
