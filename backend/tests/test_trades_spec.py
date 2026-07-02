"""Specification: multi-trade template registry."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.domain.trades.registry import get_trade_template, list_trade_options, resolve_trade_context
from app.models.enums import Industry
from app.services.onboarding_service import OnboardingService


class TradeTemplateSpecification(unittest.TestCase):
    def test_all_industries_have_templates(self) -> None:
        for industry in Industry:
            template = get_trade_template(industry)
            self.assertEqual(template.industry, industry)
            self.assertTrue(template.services)
            self.assertTrue(template.emergency_rules)

    def test_gas_engineer_has_compliance_for_gb(self) -> None:
        business = MagicMock()
        business.industry = Industry.GAS_ENGINEER
        business.country = "GB"
        ctx = resolve_trade_context(business)
        self.assertIn("Gas Safe", ctx.compliance_notes)

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
        self.assertIn("general", values)

    def test_seed_defaults_uses_business_industry(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.industry = Industry.PLASTERER

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


if __name__ == "__main__":
    unittest.main()
