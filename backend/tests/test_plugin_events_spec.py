"""Specification: domain flows publish events to the plugin event bus."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.plugins.events import Events, get_event_bus
from app.plugins.publishers import (
    publish_booking_created,
    publish_call_ended,
    publish_call_started,
    publish_payment_received,
    publish_sms_received,
    publish_sms_sent,
)
from app.services.billing_service import BillingService


class PluginEventPublishersSpecification(unittest.TestCase):
    def setUp(self) -> None:
        self.received: list[str] = []
        bus = get_event_bus()
        bus.unsubscribe("*", "test-capture")
        bus.subscribe(
            "*",
            lambda event: self.received.append(event.name),
            subscriber_id="test-capture",
        )

    def test_publish_booking_created(self) -> None:
        publish_booking_created(
            business_id="biz-1",
            appointment_id="appt-1",
            customer_id="cust-1",
            start_time="2026-07-26T10:00:00+00:00",
        )
        self.assertIn(Events.BOOKING_CREATED, self.received)

    def test_publish_sms_sent(self) -> None:
        publish_sms_sent(
            business_id="biz-1",
            to_number="+15551234567",
            provider="telnyx",
            sent=True,
        )
        self.assertIn(Events.SMS_SENT, self.received)

    def test_publish_call_lifecycle(self) -> None:
        publish_call_started(
            business_id="biz-1",
            call_log_id="call-1",
            caller_phone="+15551234567",
        )
        publish_call_ended(
            business_id="biz-1",
            call_log_id="call-1",
            status="completed",
        )
        self.assertEqual(
            [Events.CALL_STARTED, Events.CALL_ENDED],
            [name for name in self.received if name.startswith("Call")],
        )

    def test_publish_sms_received(self) -> None:
        publish_sms_received(
            business_id="biz-1",
            from_number="+15551111111",
            to_number="+15552222222",
            text="hello",
        )
        self.assertIn(Events.SMS_RECEIVED, self.received)

    @patch("app.services.billing_service.get_payment_plugin")
    def test_checkout_completed_publishes_payment_received(self, plugin_mock) -> None:
        payment = MagicMock()
        payment.is_payment_configured.return_value = True
        plugin_mock.return_value = payment

        db = MagicMock()
        business = MagicMock(id="biz-1", stripe_customer_id="cus_1")
        db.query.return_value.filter.return_value.first.return_value = business

        BillingService._handle_checkout_completed(
            db,
            {
                "customer": "cus_1",
                "subscription": "sub_1",
                "metadata": {"business_id": "biz-1", "plan_tier": "pro"},
            },
        )
        self.assertIn(Events.PAYMENT_RECEIVED, self.received)


class AppointmentEventWiringSpecification(unittest.TestCase):
    @patch("app.plugins.publishers.publish_booking_created")
    @patch("app.services.appointment_service.get_customer_for_business")
    def test_create_appointment_publishes_event(self, customer_mock, publish_mock) -> None:
        from datetime import UTC, datetime

        from app.schemas import AppointmentCreate
        from app.services.appointment_service import AppointmentService

        customer_mock.return_value = MagicMock()
        db = MagicMock()
        business = MagicMock(id="biz-1")
        start = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)
        end = datetime(2026, 7, 26, 11, 0, tzinfo=UTC)
        data = AppointmentCreate(
            customer_id="cust-1",
            service_type="Repair",
            start_time=start,
            end_time=end,
        )

        with patch.object(AppointmentService, "_validate_slot_available"):
            with patch("app.services.appointment_service.Appointment") as appt_cls:
                appt = MagicMock(id="appt-1", customer_id="cust-1", start_time=start)
                appt_cls.return_value = appt
                with patch("app.services.appointment_service.Job"):
                    AppointmentService.create_appointment(db, business, data, create_job=False)

        publish_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
