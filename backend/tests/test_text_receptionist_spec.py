"""Specification: dashboard text chat receptionist guards (voice_mode=False)."""

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


def _text_tools(
    state: VoiceSessionState,
    *,
    user_turn_count: int = 1,
) -> ReceptionistToolsImpl:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    notifications = MagicMock()
    business = sample_business()
    with patch.object(VoiceSessionState, "load", return_value=state):
        tools = ReceptionistToolsImpl(
            db,
            business,
            notifications,
            call_log_id="chat-spec-1",
            voice_mode=False,
        )
    tools.user_turn_count = user_turn_count
    return tools


class TextReceptionistFlowSpecification(unittest.IsolatedAsyncioTestCase):
    """Dashboard chat must not skip intake or book/SMS in one turn like the old bug."""

    async def test_create_customer_blocked_on_first_turn(self) -> None:
        tools = _text_tools(fresh_voice_session(), user_turn_count=1)

        result = await tools.create_customer(
            "Brian Smith",
            "+447492046947",
            address="123 Main Street, Columbus, OH 43215",
        )

        self.assertFalse(result.success)
        self.assertIn("full name", result.message.lower())

    async def test_create_customer_allowed_from_turn_two_with_caller_id(self) -> None:
        state = fresh_voice_session()
        tools = _text_tools(state, user_turn_count=2)

        customer = MagicMock()
        customer.id = "cust-text-1"
        customer.name = "Brian Smith"
        customer.phone = "+447492046947"
        customer.address = "123 Main Street, Columbus, OH 43215"

        with patch(
            "app.ai.receptionist_tools.CustomerService.lookup_by_phone",
            return_value=None,
        ), patch(
            "app.ai.receptionist_tools.CustomerService.create_customer",
            return_value=customer,
        ):
            result = await tools.create_customer(
                "Brian Smith",
                "+447492046947",
                address="123 Main Street, Columbus, OH 43215",
            )

        self.assertTrue(result.success)
        self.assertTrue(state.intake_saved_this_call)

    async def test_cannot_book_on_same_turn_as_first_availability(self) -> None:
        state = intake_complete_session()
        state.record_availability(sample_offered_slots(), voice=False)
        tools = _text_tools(state, user_turn_count=4)

        start, end, _, _ = sample_slot_times()
        book = await tools.book_appointment(
            "cust-1",
            "No hot water",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )

        self.assertFalse(book.success)
        self.assertIn("wait", book.message.lower())

    @patch("app.ai.receptionist_tools.CustomerService.lookup_by_phone", return_value=None)
    @patch("app.ai.receptionist_tools.CustomerService.create_customer")
    @patch("app.ai.receptionist_tools.AppointmentService.get_availability")
    @patch("app.ai.receptionist_tools.resolve_target_date")
    @patch("app.ai.receptionist_tools.AppointmentService.create_appointment")
    async def test_full_text_flow_across_turns(
        self,
        mock_create_appt,
        mock_resolve_date,
        mock_availability,
        mock_create_customer,
        _mock_lookup,
    ) -> None:
        """Turn 1 blocked → intake on turn 3 → slots on turn 4 → book on turn 5."""
        state = fresh_voice_session()
        start, end, _, _ = sample_slot_times()

        customer = MagicMock()
        customer.id = "cust-flow"
        customer.name = "Brian Smith"
        customer.phone = "+447492046947"
        customer.address = "123 Main Street, Columbus, OH 43215"
        mock_create_customer.return_value = customer

        mock_resolve_date.return_value = date(2026, 7, 1)
        mock_availability.return_value = [
            {"start_time": start.astimezone(UTC), "end_time": end.astimezone(UTC)},
        ]

        appt = MagicMock()
        appt.id = "appt-text-1"
        appt.start_time = start.astimezone(UTC)
        appt.end_time = end.astimezone(UTC)
        appt.status = AppointmentStatus.SCHEDULED
        mock_create_appt.return_value = appt

        turn_one = _text_tools(state, user_turn_count=1)
        blocked = await turn_one.create_customer(
            "Brian Smith",
            "+447492046947",
            address="123 Main Street, Columbus, OH 43215",
        )
        self.assertFalse(blocked.success)

        turn_three = _text_tools(state, user_turn_count=3)
        created = await turn_three.create_customer(
            "Brian Smith",
            "+447492046947",
            address="123 Main Street, Columbus, OH 43215",
        )
        self.assertTrue(created.success)

        turn_four = _text_tools(state, user_turn_count=4)
        slots = await turn_four.check_availability("tomorrow", "Water heater repair")
        self.assertTrue(slots.success)
        self.assertGreater(slots.data["count"], 0)

        same_turn_book = await turn_four.book_appointment(
            "cust-flow",
            "Water heater repair",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertFalse(same_turn_book.success)

        turn_five = _text_tools(ready_to_book_session("cust-flow"), user_turn_count=5)
        booked = await turn_five.book_appointment(
            "cust-flow",
            "Water heater repair",
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertTrue(booked.success)
        mock_create_appt.assert_called_once()

    async def test_duplicate_send_sms_blocked(self) -> None:
        state = fresh_voice_session()
        state.sms_sent_this_call = True
        tools = _text_tools(state, user_turn_count=6)

        result = await tools.send_sms("+447492046947", "Your appointment is confirmed.")

        self.assertFalse(result.success)
        self.assertIn("already sent", result.message.lower())
        tools.notifications.send_sms.assert_not_called()
