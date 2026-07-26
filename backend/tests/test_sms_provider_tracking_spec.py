"""Specification: outbound SMS records provider on sms_logs."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.communication_service import CommunicationService
from app.services.notification_service import NotificationService
from tests.fakes.fake_providers import FakeMessagingProvider


class SmsProviderTrackingSpecification(unittest.TestCase):
    @patch("app.services.notification_service.get_sms_provider_for_business")
    def test_notification_service_records_provider_on_send(self, provider_mock) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.phone_number = "+15551111111"

        sms_provider = MagicMock()
        sms_provider.provider_name = "telnyx"
        sms_provider.is_configured.return_value = True
        sms_provider.send_sms.return_value = {
            "sent": True,
            "provider": "telnyx",
            "id": "sms-123",
        }
        provider_mock.return_value = sms_provider

        with patch("app.services.notification_service.get_settings") as settings_mock:
            settings_mock.return_value = MagicMock(telnyx_messaging_profile_id="mp-1")
            service = NotificationService(db, business)
            result = service.send_sms("+15552222222", "Hello")

        self.assertTrue(result["sent"])
        self.assertEqual(result["provider"], "telnyx")
        db.add.assert_called_once()
        record = db.add.call_args[0][0]
        self.assertEqual(record.provider, "telnyx")
        self.assertEqual(record.business_id, "biz-1")
        self.assertEqual(record.to_number, "+15552222222")
        self.assertTrue(record.sent)
        db.commit.assert_called_once()

    @patch("app.services.notification_service.get_sms_provider_for_business")
    def test_notification_service_records_dev_log_provider(self, provider_mock) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.phone_number = None

        sms_provider = MagicMock()
        sms_provider.provider_name = "dev_log"
        sms_provider.is_configured.return_value = True
        provider_mock.return_value = sms_provider

        service = NotificationService(db, business)
        result = service.send_sms("+15552222222", "Hello")

        self.assertEqual(result["provider"], "dev_log")
        record = db.add.call_args[0][0]
        self.assertEqual(record.provider, "dev_log")

    def test_communication_service_records_provider_when_db_available(self) -> None:
        db = MagicMock()
        messaging = FakeMessagingProvider()
        service = CommunicationService(messaging, db=db, business_id="biz-1")

        result = service.send_sms(from_number="+1", to_number="+2", text="hello")

        self.assertEqual(result["provider"], "mock")
        db.add.assert_called_once()
        record = db.add.call_args[0][0]
        self.assertEqual(record.provider, "mock")
        self.assertEqual(record.business_id, "biz-1")


if __name__ == "__main__":
    unittest.main()
