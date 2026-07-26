"""Specification: per-business provider_config overrides."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.domain.provider_config import merge_provider_config
from app.schemas import BusinessUpdate
from app.services.business_service import BusinessServiceManager
from app.services.provider_settings_service import ProviderSettingsService


REGISTERED = {
    "telephony": ["telnyx", "twilio", "vonage"],
    "numbers": ["telnyx", "twilio", "vonage"],
    "regulatory": ["telnyx", "twilio", "vonage"],
    "voice": ["openai"],
    "messaging": ["composite", "local", "telnyx"],
    "storage": ["local"],
}


class ProviderConfigDomainSpecification(unittest.TestCase):
    def test_merge_adds_valid_override(self) -> None:
        result = merge_provider_config(
            {},
            {"telephony": "twilio"},
            registered=REGISTERED,
        )
        self.assertEqual(result, {"telephony": "twilio"})

    def test_merge_clears_override_with_auto(self) -> None:
        result = merge_provider_config(
            {"telephony": "twilio"},
            {"telephony": "auto"},
            registered=REGISTERED,
        )
        self.assertEqual(result, {})

    def test_merge_rejects_unknown_service(self) -> None:
        with self.assertRaises(ValueError):
            merge_provider_config({}, {"unknown": "telnyx"}, registered=REGISTERED)

    def test_merge_rejects_unregistered_provider(self) -> None:
        with self.assertRaises(ValueError):
            merge_provider_config({}, {"telephony": "bandwidth"}, registered=REGISTERED)


class ProviderConfigBusinessServiceSpecification(unittest.TestCase):
    def test_update_business_persists_provider_config(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_provisioned = False
        business.provider_config = {}

        with unittest.mock.patch(
            "app.providers.factory.list_provider_registry",
            return_value=REGISTERED,
        ):
            BusinessServiceManager.update_business(
                db,
                business,
                BusinessUpdate(provider_config={"telephony": "twilio"}),
            )

        self.assertEqual(business.provider_config, {"telephony": "twilio"})
        db.commit.assert_called_once()

    def test_update_business_rejects_invalid_provider(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_provisioned = False
        business.provider_config = {}

        with unittest.mock.patch(
            "app.providers.factory.list_provider_registry",
            return_value=REGISTERED,
        ):
            with self.assertRaises(HTTPException) as ctx:
                BusinessServiceManager.update_business(
                    db,
                    business,
                    BusinessUpdate(provider_config={"telephony": "bandwidth"}),
                )

        self.assertEqual(ctx.exception.status_code, 400)


class ProviderSettingsServiceSpecification(unittest.TestCase):
    def test_get_settings_includes_overrides_and_defaults(self) -> None:
        business = MagicMock()
        business.country = "US"
        business.provider_config = {"telephony": "twilio"}

        settings = ProviderSettingsService.get_settings(business)

        self.assertEqual(settings["provider_config"]["telephony"], "twilio")
        self.assertIn("telephony", settings["country_defaults"])
        self.assertIn("telnyx", settings["available"]["telephony"])


if __name__ == "__main__":
    unittest.main()
