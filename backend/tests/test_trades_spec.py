"""Specification: multi-trade template registry and integrations."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.ai.prompts import build_receptionist_prompt
from app.domain.intake import is_valid_customer_name
from app.domain.telecom import get_supported_countries
from app.domain.trades.compliance import get_compliance_notes
from app.domain.trades.registry import get_trade_template, list_trade_options, resolve_trade_context
from app.models.enums import Industry
from app.services.conversation_service import ConversationService
from app.services.onboarding_service import OnboardingService
from app.voice.gather_prompts import empty_gather_prompt
from app.voice.texml_builder import build_greeting
from tests.helpers import sample_business


class TradeTemplateSpecification(unittest.TestCase):
    def test_all_industries_have_templates(self) -> None:
        for industry in Industry:
            template = get_trade_template(industry)
            self.assertEqual(template.industry, industry)
            self.assertTrue(template.services)
            self.assertTrue(template.emergency_rules)

    def test_gas_engineer_has_compliance_for_gb(self) -> None:
        ctx = resolve_trade_context(
            sample_business(industry=Industry.GAS_ENGINEER, country="GB")
        )
        self.assertIn("Gas Safe", ctx.compliance_notes)

    def test_gas_engineer_has_compliance_for_us(self) -> None:
        notes = get_compliance_notes(Industry.GAS_ENGINEER, "US")
        self.assertIn("911", notes)

    def test_plumbing_seed_differs_from_mobile_mechanic(self) -> None:
        plumbing = get_trade_template(Industry.PLUMBING)
        mechanic = get_trade_template(Industry.MOBILE_MECHANIC)
        self.assertNotEqual(
            [s.name for s in plumbing.services],
            [s.name for s in mechanic.services],
        )

    def test_list_trade_options_includes_core_trades(self) -> None:
        values = {item["value"] for item in list_trade_options()}
        self.assertIn("plumbing", values)
        self.assertIn("mobile_mechanic", values)
        self.assertIn("gas_engineer", values)
        self.assertIn("plasterer", values)
        self.assertIn("general", values)

    def test_trade_options_include_service_previews(self) -> None:
        plumbing = next(t for t in list_trade_options() if t["value"] == "plumbing")
        self.assertIn("Drain cleaning", plumbing["services"])
        self.assertTrue(plumbing["emergency_rules"])

    def test_template_creates_valid_seed_schemas(self) -> None:
        template = get_trade_template(Industry.LOCKSMITH)
        services = template.service_creates()
        rules = template.rule_creates()
        self.assertEqual(services[0].name, "Lockout service")
        self.assertIn("child locked", rules[0].keywords)

    def test_seed_defaults_uses_business_industry(self) -> None:
        db = MagicMock()
        business = sample_business(industry=Industry.PLASTERER)

        with unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.list_services",
            return_value=[],
        ), unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.list_emergency_rules",
            return_value=[],
        ), unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.add_service",
        ) as add_svc, unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.add_emergency_rule",
        ):
            result = OnboardingService.seed_defaults(db, business)

        self.assertEqual(result["industry"], "plasterer")
        self.assertGreater(result["services"], 0)
        first_call = add_svc.call_args_list[0][0][2]
        self.assertEqual(first_call.name, "Patch repair")

    def test_seed_defaults_skips_when_services_exist(self) -> None:
        db = MagicMock()
        business = sample_business(industry=Industry.HVAC)

        with unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.list_services",
            return_value=[MagicMock()],
        ), unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.list_emergency_rules",
            return_value=[MagicMock()],
        ), unittest.mock.patch(
            "app.services.onboarding_service.BusinessServiceManager.add_service",
        ) as add_svc:
            result = OnboardingService.seed_defaults(db, business)

        self.assertEqual(result["services"], 0)
        self.assertEqual(result["emergency_rules"], 0)
        add_svc.assert_not_called()


class TradePromptIntegrationSpecification(unittest.TestCase):
    def test_prompt_uses_trade_label(self) -> None:
        business = sample_business(industry=Industry.MOBILE_MECHANIC)
        prompt = build_receptionist_prompt(business, [], [], voice_mode=True)
        self.assertIn("Mobile mechanic business", prompt)
        self.assertIn("won't start", prompt.lower())

    def test_prompt_includes_regional_compliance_block(self) -> None:
        business = sample_business(industry=Industry.GAS_ENGINEER, country="GB")
        prompt = build_receptionist_prompt(business, [], [], voice_mode=False)
        self.assertIn("Regulatory compliance", prompt)
        self.assertIn("Gas Safe", prompt)

    def test_prompt_uses_template_fallback_without_services(self) -> None:
        business = sample_business(industry=Industry.PLASTERER)
        prompt = build_receptionist_prompt(business, [], [], voice_mode=False)
        self.assertIn("General plastering job", prompt)
        self.assertIn("Ceiling collapse risk", prompt)

    def test_prompt_uses_gb_address_hint(self) -> None:
        business = sample_business(industry=Industry.PLUMBING, country="GB")
        prompt = build_receptionist_prompt(business, [], [], voice_mode=False)
        self.assertIn("postcode", prompt.lower())


class TradeVoiceIntegrationSpecification(unittest.TestCase):
    def test_build_greeting_uses_trade_example(self) -> None:
        business = sample_business(
            industry=Industry.MOBILE_MECHANIC,
            name="Road Rescue",
        )
        texml = build_greeting(business, "http://localhost:8000", "call-1")
        self.assertIn("Road Rescue", texml)
        self.assertIn("will not start", texml.lower())

    def test_empty_gather_prompt_uses_trade_example(self) -> None:
        call_log = MagicMock(conversation_history=[])
        trade = resolve_trade_context(sample_business(industry=Industry.GAS_ENGINEER))
        prompt = empty_gather_prompt(call_log, trade)
        self.assertIn("no heating", prompt.lower())


class TradeIntakeIntegrationSpecification(unittest.TestCase):
    def test_rejects_plumbing_garbled_name(self) -> None:
        self.assertFalse(
            is_valid_customer_name("clogged drain", industry=Industry.PLUMBING)
        )

    def test_rejects_mechanic_garbled_name(self) -> None:
        self.assertFalse(
            is_valid_customer_name("flat battery", industry=Industry.MOBILE_MECHANIC)
        )

    def test_accepts_real_name_for_any_trade(self) -> None:
        self.assertTrue(
            is_valid_customer_name("Brian Smith", industry=Industry.GAS_ENGINEER)
        )


class TradeConversationIntegrationSpecification(unittest.TestCase):
    def test_emergency_detection_uses_trade_keywords(self) -> None:
        db = MagicMock()
        business = sample_business(industry=Industry.GAS_ENGINEER)
        db.query.return_value.filter.return_value.first.return_value = business

        call = MagicMock()
        call.business_id = business.id
        call.conversation_history = [
            {"role": "user", "content": "I smell gas in the kitchen"},
        ]

        self.assertTrue(ConversationService._looks_emergency(call, db))

    def test_service_inference_uses_trade_keywords(self) -> None:
        db = MagicMock()
        business = sample_business(industry=Industry.MOBILE_MECHANIC)
        db.query.return_value.filter.return_value.first.return_value = business

        call = MagicMock()
        call.business_id = business.id
        call.conversation_history = [
            {"role": "user", "content": "My car battery is completely dead"},
        ]

        inferred = ConversationService._infer_service_from_history(call, db)
        self.assertIsNotNone(inferred)
        self.assertIn("battery", inferred.lower())


class SupportedCountriesSpecification(unittest.TestCase):
    def test_get_supported_countries_includes_major_markets(self) -> None:
        codes = {c["code"] for c in get_supported_countries()}
        for expected in ("US", "GB", "AU", "DE"):
            self.assertIn(expected, codes)

    def test_country_entries_have_labels(self) -> None:
        for entry in get_supported_countries():
            self.assertTrue(entry["code"])
            self.assertTrue(entry["label"])


if __name__ == "__main__":
    unittest.main()
