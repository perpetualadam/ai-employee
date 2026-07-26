"""Specification: integration registry — composition root for swappable adapters."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.integrations.registry import (
    get_ai_provider,
    get_email_provider,
    get_sms_inbound_adapter,
    get_sms_provider,
    get_voice_call_control,
    get_voice_webhook_adapter,
    list_registered_integrations,
)


class IntegrationRegistrySpecification(unittest.TestCase):
    @patch("app.integrations.registry.get_settings")
    def test_registry_returns_provider_instances(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(
            groq_api_key="test-key",
            groq_model="test-model",
            ai_provider="groq",
            voice_provider="telnyx",
            sms_provider="telnyx",
            email_provider="dev",
        )
        self.assertIn(get_sms_provider().provider_name, ("telnyx", "dev_log"))
        self.assertEqual(get_voice_call_control().provider_name, "telnyx")
        self.assertEqual(get_voice_webhook_adapter().provider_name, "telnyx")
        self.assertEqual(get_sms_inbound_adapter().provider_name, "telnyx")
        self.assertIn(get_email_provider().provider_name, ("smtp", "dev_log"))
        self.assertIsNotNone(get_ai_provider())

    def test_list_registered_integrations(self) -> None:
        registered = list_registered_integrations()
        self.assertIn("telnyx", registered["voice"])
        self.assertIn("groq", registered["ai"])
        self.assertIn("smtp", registered["email"])


if __name__ == "__main__":
    unittest.main()
