"""Specification: CallService wired into outbound and live transfer paths."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.call_service import CallService
from app.services.outbound_call_service import OutboundCallService
from tests.fakes.fake_providers import FakeTelephonyProvider


class CallServiceSpecification(unittest.TestCase):
    def test_place_outbound_call_delegates_to_provider(self) -> None:
        provider = FakeTelephonyProvider()
        service = CallService(provider)

        async def run() -> dict:
            return await service.place_outbound_call(
                from_number="+15551111111",
                to_number="+15552222222",
                webhook_url="https://example.test/voice/outbound",
            )

        import asyncio

        result = asyncio.run(run())
        self.assertEqual(result["call_id"], "call-mock-1")
        self.assertEqual(result["provider"], "mock")

    def test_transfer_call_delegates_to_provider(self) -> None:
        provider = FakeTelephonyProvider()
        service = CallService(provider)

        async def run() -> dict:
            return await service.transfer_call("call-abc", "+15553333333")

        import asyncio

        result = asyncio.run(run())
        self.assertEqual(result["call_id"], "call-abc")

    @patch("app.services.outbound_call_service.get_call_service")
    def test_outbound_call_service_uses_call_service(self, get_service_mock) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_number = "+15551111111"

        call_service = MagicMock()
        call_service.is_configured.return_value = True
        call_service.place_outbound_call = AsyncMock(
            return_value={"call_id": "ext-99", "provider": "fake"}
        )
        get_service_mock.return_value = call_service

        db.refresh = MagicMock()

        with patch("app.services.outbound_call_service.get_settings") as settings_mock:
            settings_mock.return_value.public_api_url = "http://localhost:8000"
            settings_mock.return_value.api_v1_prefix = "/api/v1"
            result = OutboundCallService.initiate_callback(
                db,
                business,
                phone="+15552222222",
                reason="Callback",
            )

        call_service.place_outbound_call.assert_called_once()
        self.assertEqual(result.external_call_id, "ext-99")


if __name__ == "__main__":
    unittest.main()
