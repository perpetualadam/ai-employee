"""Specification: P4 — reminders, outbound calls, monitoring."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.reminder_service import ReminderService
from app.services.voice_mode_service import VoiceModeService


class ReminderServiceSpecification(unittest.TestCase):
    def test_due_appointments_respects_window(self) -> None:
        db = MagicMock()
        appt = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
            appt
        ]

        with patch("app.services.reminder_service.get_settings") as settings_mock:
            settings_mock.return_value.reminder_hours_before = 24
            results = ReminderService.due_appointments(db)

        self.assertEqual(len(results), 1)


class VoiceModeServiceSpecification(unittest.TestCase):
    def test_stream_falls_back_to_gather_without_stt_plugin(self) -> None:
        markup = MagicMock()
        markup.supports_streaming.return_value = True
        markup.is_configured.return_value = True
        with patch("app.services.voice_mode_service.get_settings") as settings_mock:
            settings_mock.return_value.voice_mode = "stream"
            with patch(
                "app.services.voice_mode_service.get_speech_to_text_plugin",
                return_value=None,
            ):
                with patch(
                    "app.services.voice_mode_service.resolve_voice_markup",
                    return_value=markup,
                ):
                    self.assertEqual(VoiceModeService.effective_mode(), "gather")

    def test_stream_active_when_stt_and_markup_configured(self) -> None:
        stt = MagicMock()
        stt.is_configured.return_value = True
        markup = MagicMock()
        markup.supports_streaming.return_value = True
        markup.is_configured.return_value = True
        with patch("app.services.voice_mode_service.get_settings") as settings_mock:
            settings_mock.return_value.voice_mode = "stream"
            with patch(
                "app.services.voice_mode_service.get_speech_to_text_plugin",
                return_value=stt,
            ):
                with patch(
                    "app.services.voice_mode_service.resolve_voice_markup",
                    return_value=markup,
                ):
                    self.assertEqual(VoiceModeService.effective_mode(), "stream")

    def test_status_includes_recommendation(self) -> None:
        status = VoiceModeService.status()
        self.assertIn("effective_mode", status)
        self.assertIn("speech_to_text_configured", status)
        self.assertEqual(status["production_recommendation"], "gather")


class OutboundCallSpecification(unittest.TestCase):
    @patch("app.services.outbound_call_service.get_call_service")
    def test_initiate_callback_creates_call_log(self, get_service_mock) -> None:
        from app.services.outbound_call_service import OutboundCallService

        call_service = MagicMock()
        call_service.is_configured.return_value = True
        call_service.place_outbound_call = AsyncMock(return_value={"call_id": "call-abc"})
        get_service_mock.return_value = call_service

        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.phone_number = "+15551234567"
        business.country = "US"
        business.escalation_phone = "+15559876543"

        customer = MagicMock()
        customer.id = "cust-1"
        customer.phone = "+15551112222"

        with patch(
            "app.services.outbound_call_service.CustomerService.get_customer",
            return_value=customer,
        ):
            with patch("app.services.outbound_call_service.get_settings") as settings_mock:
                settings_mock.return_value.public_api_url = "http://localhost:8000"
                settings_mock.return_value.api_v1_prefix = "/api/v1"
                call_log = OutboundCallService.initiate_callback(
                    db,
                    business,
                    customer_id="cust-1",
                )

        self.assertEqual(call_log.external_call_id, "call-abc")
        call_service.place_outbound_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
