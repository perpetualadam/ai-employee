"""Specification: voice session guards between intake, availability, and booking."""

import unittest
from datetime import UTC

from app.ai.tools import ToolResult
from app.voice.session_state import VoiceSessionState
from tests.helpers import intake_complete_session, ready_to_book_session, sample_offered_slots, sample_slot_times


class VoiceSessionSpecification(unittest.TestCase):
    """Phone-call session rules that must hold after the modular refactor."""

    def test_blocks_availability_without_create_customer_on_call(self) -> None:
        state = VoiceSessionState(caller_phone="+447492046947")
        block = state.require_intake("check availability")
        self.assertIsInstance(block, ToolResult)
        self.assertFalse(block.success)
        self.assertIn("create_customer", block.message)

    def test_blocks_booking_without_create_customer_on_call(self) -> None:
        state = VoiceSessionState(
            verified_customer_id="stale-id",
            name_collected=True,
            address_collected=True,
        )
        block = state.require_intake("book")
        self.assertIsInstance(block, ToolResult)
        self.assertFalse(block.success)

    def test_blocks_booking_same_turn_as_first_availability_check(self) -> None:
        state = intake_complete_session()
        state.record_availability(sample_offered_slots())
        block = state.block_same_turn_booking()
        self.assertIsInstance(block, ToolResult)
        self.assertFalse(block.success)
        self.assertIn("wait", block.message.lower())

    def test_allows_booking_on_next_turn_after_slots_offered(self) -> None:
        state = ready_to_book_session()
        self.assertIsNone(state.block_same_turn_booking())

    def test_rejects_booking_time_not_in_offered_slots(self) -> None:
        state = ready_to_book_session()
        start, end, _, _ = sample_slot_times()
        wrong_start = start.replace(minute=0).astimezone(UTC)
        wrong_end = end.replace(minute=0).astimezone(UTC)

        result = state.validate_and_resolve_slot(wrong_start, wrong_end)
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIn("11:30 AM", result.message)

    def test_accepts_exact_offered_slot_for_booking(self) -> None:
        state = ready_to_book_session()
        start, end, _, _ = sample_slot_times()
        result = state.validate_and_resolve_slot(
            start.astimezone(UTC),
            end.astimezone(UTC),
        )
        self.assertIsInstance(result, tuple)
        resolved_start, resolved_end = result
        self.assertEqual(resolved_start, start.astimezone(UTC))

    def test_restores_offered_slots_from_prior_check_availability_log(self) -> None:
        state = VoiceSessionState()
        log = type("Log", (), {})()
        log.tool_name = "check_availability"
        log.output_data = {
            "success": True,
            "data": {"slots": sample_offered_slots()},
        }
        state.apply_voice_activity_log(log)
        self.assertTrue(state.prior_availability_check)
        self.assertEqual(len(state.offered_slots), 2)
        self.assertEqual(state.offered_slots[0]["spoken_time"], "11:30 AM")


if __name__ == "__main__":
    unittest.main()
