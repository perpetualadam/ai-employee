"""Specification: legacy integrations registry resolves providers via ProviderConfiguration."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.integrations.contracts import VoiceCallControl
from app.integrations.provider_resolution import (
    resolve_sms_cpaas_name,
    resolve_sms_outbound_name,
    resolve_telephony_adapter_name,
)
from app.integrations.registry import (
    get_sms_inbound_adapter,
    get_sms_provider,
    get_voice_call_control,
    get_voice_webhook_adapter,
    register_voice_control,
)
from app.providers.configuration import ProviderConfiguration


class _StubVoiceControl(VoiceCallControl):
    def __init__(self, name: str = "stub") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        return None


def _test_config(*, telephony: str = "telnyx", messaging: str = "telnyx") -> ProviderConfiguration:
    return ProviderConfiguration(
        {
            "defaults": {
                "telephony": telephony,
                "messaging": messaging,
            },
            "countries": {
                "US": {"telephony": telephony, "messaging": messaging},
                "GB": {"telephony": telephony, "messaging": messaging},
            },
            "failover": {
                "telephony": [telephony],
                "messaging": [messaging, "dev"],
            },
        }
    )


class IntegrationProviderResolutionSpecification(unittest.TestCase):
    def setUp(self) -> None:
        from app.integrations.registry import _voice_control

        _voice_control.cache_clear()

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_auto_mode_uses_country_telephony_config(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="telnyx")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")
        business = MagicMock(country="US", provider_config={})

        self.assertEqual(resolve_telephony_adapter_name(business=business), "telnyx")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_business_provider_config_overrides_country(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="telnyx")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")
        business = MagicMock(country="US", provider_config={"telephony": "stub"})

        self.assertEqual(resolve_telephony_adapter_name(business=business), "stub")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_env_override_wins_over_configuration(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="telnyx")
        settings_mock.return_value = MagicMock(voice_provider="stub", sms_provider="auto")

        self.assertEqual(resolve_telephony_adapter_name(), "stub")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_composite_messaging_resolves_sms_cpaas_to_telephony(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="telnyx", messaging="composite")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")
        business = MagicMock(country="US", provider_config={})

        self.assertEqual(resolve_sms_cpaas_name(business=business), "telnyx")

    @patch("app.integrations.provider_resolution.get_settings")
    def test_dev_env_forces_dev_outbound_sms(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(sms_provider="dev", voice_provider="auto")

        self.assertEqual(resolve_sms_outbound_name(), "dev")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_get_voice_call_control_uses_registered_stub_adapter(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="stub")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")
        register_voice_control("stub", _StubVoiceControl)
        business = MagicMock(country="US", provider_config={"telephony": "stub"})

        control = get_voice_call_control(business=business)

        self.assertEqual(control.provider_name, "stub")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_webhook_and_inbound_follow_telephony_resolution(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(telephony="telnyx", messaging="telnyx")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")

        self.assertEqual(get_voice_webhook_adapter().provider_name, "telnyx")
        self.assertEqual(get_sms_inbound_adapter().provider_name, "telnyx")

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_get_sms_provider_from_configuration(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        config_mock.return_value = _test_config(messaging="telnyx")
        settings_mock.return_value = MagicMock(voice_provider="auto", sms_provider="auto")

        self.assertIn(get_sms_provider().provider_name, ("telnyx", "dev_log"))


if __name__ == "__main__":
    unittest.main()
