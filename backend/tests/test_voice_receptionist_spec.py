"""Specification: end-to-end voice receptionist tool flow (intake → slots → book)."""

from __future__ import annotations

import unittest
from datetime import UTC, date
from unittest.mock import MagicMock, patch

from app.ai.receptionist_tools import ReceptionistToolsImpl
from app.models.enums import AppointmentStatus
from app.voice.session_state import VoiceSessionState
from tests.helpers import (
    fresh_voice_session,
    intake_complete_session,
    ready_to_book_session,
    sample_business,
    sample_offered_slots,
    sample_slot_times,
)


def _voice_tools(state: VoiceSessionState) -> ReceptionistToolsImpl:
    db = MagicMock()
    notifications = MagicMock()
    business = sample_business()
    with patch.object(VoiceSessionState, "load", return_value=state):
        tools = ReceptionistToolsImpl(
            db,
            business,
            notifications,
            call_log_id="call-spec-1",
            voice_mode=True,
        )
    return tools


class VoiceReceptionistFlowSpecification(unittest.IsolatedAsyncioTestCase):
    """
    How an inbound plumber call should work — these tests define expected behavior,
    not merely document current bugs.
    """

    async def test_lookup_alone_must_not_enable_booking(self) -> None:
        """Even when CRM has a matching record, voice calls require fresh create_customer."""
        existing = MagicMock()
        existing.id = "cust-existing"
        existing.name = "Brian Smith"
        existing.phone = "+447492046947"
        existing.address = "123 Main Street, Columbus, OH 43215"
        existing.email = None

        state = fresh_voice_session()
        tools = _voice_tools(state)

        with patch(
            "app.ai.receptionist_tools.CustomerService.lookup_by_phone",
            return_value=existing,
        ):
            lookup = await tools.lookup_customer("+447492046947")

        self.assertTrue(lookup.success)
        self.assertIn("create_customer", lookup.message)
        self.assertFalse(state.intake_saved_this_call)

        start, end, _, _ = sample_slot_times()
        book = await tools.book_appointment(
            "cust-existing",
            "Drain cleaning",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertFalse(book.success)
        self.assertIn("create_customer", book.message)

    async def test_create_customer_rejects_incomplete_intake(self) -> None:
        tools = _voice_tools(fresh_voice_session())

        name_only = await tools.create_customer(
            "Brian Smith",
            "+447492046947",
            address="Michigan",
        )
        self.assertFalse(name_only.success)
        self.assertIn("street", name_only.message.lower())

        placeholder = await tools.create_customer(
            "Caller",
            "+447492046947",
            address="123 Main Street, Columbus, OH",
        )
        self.assertFalse(placeholder.success)
        self.assertIn("name", placeholder.message.lower())

    @patch("app.ai.receptionist_tools.CustomerService.lookup_by_phone", return_value=None)
    @patch("app.ai.receptionist_tools.CustomerService.create_customer")
    async def test_happy_path_intake_then_availability(self, mock_create, _mock_lookup) -> None:
        """After valid create_customer, availability returns spoken slot times."""
        customer = MagicMock()
        customer.id = "cust-new"
        customer.name = "Brian Smith"
        customer.phone = "+447492046947"
        customer.address = "123 Main Street, Columbus, OH 43215"
        mock_create.return_value = customer

        state = fresh_voice_session()
        tools = _voice_tools(state)

        created = await tools.create_customer(
            "Brian Smith",
            "+447492046947",
            address="123 Main Street, Columbus, OH 43215",
        )
        self.assertTrue(created.success)
        self.assertTrue(state.intake_saved_this_call)

        start, end, _, _ = sample_slot_times()
        raw_slots = [{"start_time": start.astimezone(UTC), "end_time": end.astimezone(UTC)}]
        with patch(
            "app.ai.receptionist_tools.AppointmentService.get_availability",
            return_value=raw_slots,
        ), patch(
            "app.ai.receptionist_tools.resolve_target_date",
            return_value=date(2026, 7, 1),
        ):
            availability = await tools.check_availability("tomorrow", "Drain cleaning")

        self.assertTrue(availability.success)
        self.assertIn("spoken_time", availability.data["slots"][0])
        self.assertIn("11:30 AM", availability.message)

    async def test_cannot_book_on_same_turn_as_first_availability(self) -> None:
        state = intake_complete_session()
        state.record_availability(sample_offered_slots())
        tools = _voice_tools(state)

        start, end, _, _ = sample_slot_times()
        book = await tools.book_appointment(
            "cust-1",
            "Kitchen leak",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertFalse(book.success)
        self.assertIn("wait", book.message.lower())

    @patch("app.ai.receptionist_tools.AppointmentService.create_appointment")
    async def test_books_exact_offered_slot_not_rounded_time(self, mock_create) -> None:
        """Caller who picks 11:30 AM must get 11:30 booked — not 11:00."""
        start, end, _, _ = sample_slot_times()
        appt = MagicMock()
        appt.id = "appt-1"
        appt.start_time = start.astimezone(UTC)
        appt.end_time = end.astimezone(UTC)
        appt.status = AppointmentStatus.SCHEDULED
        mock_create.return_value = appt

        state = ready_to_book_session()
        tools = _voice_tools(state)

        wrong_start = start.replace(minute=0).astimezone(UTC)
        wrong_end = end.replace(minute=0).astimezone(UTC)
        rejected = await tools.book_appointment(
            "cust-1",
            "Kitchen leak",
            wrong_start,
            wrong_end,
        )
        self.assertFalse(rejected.success)
        self.assertIn("11:30 AM", rejected.message)
        mock_create.assert_not_called()

        accepted = await tools.book_appointment(
            "cust-1",
            "Kitchen leak",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertTrue(accepted.success)
        mock_create.assert_called_once()
        booked = mock_create.call_args[0][2]
        self.assertEqual(booked.start_time, start.astimezone(UTC))

    @patch("app.ai.receptionist_tools.AppointmentService.create_appointment")
    async def test_dispatch_uses_start_time_utc_from_slot(self, mock_create) -> None:
        """Tool dispatch must accept start_time_utc / end_time_utc from check_availability."""
        start, end, _, _ = sample_slot_times()
        appt = MagicMock()
        appt.id = "appt-2"
        appt.start_time = start.astimezone(UTC)
        appt.end_time = end.astimezone(UTC)
        appt.status = AppointmentStatus.SCHEDULED
        mock_create.return_value = appt

        tools = _voice_tools(ready_to_book_session())
        slots = sample_offered_slots()

        result = await tools.dispatch(
            "book_appointment",
            {
                "customer_id": "cust-1",
                "service_type": "Drain cleaning",
                "start_time_utc": slots[0]["start_time_utc"],
                "end_time_utc": slots[0]["end_time_utc"],
            },
        )
        self.assertTrue(result.success)
        mock_create.assert_called_once()

    @patch("app.ai.receptionist_tools.CustomerService.lookup_by_phone", return_value=None)
    @patch("app.ai.receptionist_tools.AppointmentService.create_appointment")
    @patch("app.ai.receptionist_tools.AppointmentService.get_availability")
    @patch("app.ai.receptionist_tools.CustomerService.create_customer")
    async def test_full_voice_booking_flow_across_turns(
        self,
        mock_create_customer,
        mock_get_availability,
        mock_create_appointment,
        _mock_lookup,
    ) -> None:
        """
        Spec: intake → offer slots → caller picks time on next turn → exact booking.
        Mirrors the live-call checklist without needing Telnyx.
        """
        customer = MagicMock()
        customer.id = "cust-flow"
        customer.name = "Brian Smith"
        customer.phone = "+447492046947"
        customer.address = "123 Main Street, Columbus, OH 43215"
        mock_create_customer.return_value = customer

        start, end, _, _ = sample_slot_times()
        mock_get_availability.return_value = [
            {"start_time": start.astimezone(UTC), "end_time": end.astimezone(UTC)},
        ]

        appt = MagicMock()
        appt.id = "appt-flow"
        appt.start_time = start.astimezone(UTC)
        appt.end_time = end.astimezone(UTC)
        appt.status = AppointmentStatus.SCHEDULED
        mock_create_appointment.return_value = appt

        state = fresh_voice_session()
        tools = _voice_tools(state)

        with patch(
            "app.ai.receptionist_tools.resolve_target_date",
            return_value=date(2026, 7, 1),
        ):
            created = await tools.create_customer(
                "Brian Smith",
                "+447492046947",
                address="123 Main Street, Columbus, OH 43215",
            )
            availability = await tools.check_availability("tomorrow", "Kitchen leak")

        self.assertTrue(created.success)
        self.assertTrue(availability.success)
        self.assertIn("11:30 AM", availability.message)

        blocked = await tools.book_appointment(
            "cust-flow",
            "Kitchen leak",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertFalse(blocked.success)

        state.prior_availability_check = True
        state.availability_checked_this_turn = False

        booked = await tools.book_appointment(
            "cust-flow",
            "Kitchen leak",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertTrue(booked.success)
        self.assertTrue(state.booking_complete)
        mock_create_appointment.assert_called_once()

    @patch("app.ai.receptionist_tools.CustomerService.lookup_by_phone")
    async def test_stale_test_record_requires_valid_intake_before_booking(
        self, mock_lookup
    ) -> None:
        """Old test CRM rows with placeholder data must not bypass intake."""
        stale = MagicMock()
        stale.id = "cust-stale"
        stale.name = "Caller"
        stale.phone = "+447492046947"
        stale.address = "Michigan"
        stale.email = None
        mock_lookup.return_value = stale

        def apply_update(db, customer, data):
            if getattr(data, "name", None):
                customer.name = data.name
            if getattr(data, "address", None):
                customer.address = data.address
            return customer

        state = fresh_voice_session()
        tools = _voice_tools(state)

        rejected = await tools.create_customer(
            "Caller",
            "+447492046947",
            address="Michigan",
        )
        self.assertFalse(rejected.success)

        with patch(
            "app.ai.receptionist_tools.CustomerService.update_customer",
            side_effect=apply_update,
        ):
            saved = await tools.create_customer(
                "Brian Smith",
                "+447492046947",
                address="456 Oak Avenue, Detroit, MI 48201",
            )

        self.assertTrue(saved.success)
        self.assertTrue(state.intake_saved_this_call)
        self.assertEqual(saved.data["name"], "Brian Smith")


if __name__ == "__main__":
    unittest.main()
