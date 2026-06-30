"""Specification: offered slot times must be spoken and booked exactly."""

import unittest
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.voice.slots import (
    format_slots_for_voice,
    resolve_offered_slot,
    spoken_local_time,
    voice_availability_message,
)
from tests.helpers import sample_offered_slots, sample_slot_times


class SlotBookingSpecification(unittest.TestCase):
    """Voice booking must use exact UTC times from offered slots, not rounded guesses."""

    def test_spoken_time_matches_local_slot(self) -> None:
        start, _, _, _ = sample_slot_times()
        self.assertEqual(spoken_local_time(start), "11:30 AM")

    def test_formatted_slots_include_utc_and_spoken_time(self) -> None:
        start, end, _, _ = sample_slot_times()
        raw = [{"start_time": start.astimezone(UTC), "end_time": end.astimezone(UTC)}]
        formatted = format_slots_for_voice(raw, ZoneInfo("America/New_York"))
        self.assertEqual(formatted[0]["spoken_time"], "11:30 AM")
        self.assertIn("start_time_utc", formatted[0])
        self.assertIn("end_time_utc", formatted[0])

    def test_availability_message_forbids_inventing_times(self) -> None:
        msg = voice_availability_message(sample_offered_slots())
        self.assertIn("11:30 AM", msg)
        self.assertIn("start_time_utc", msg)
        self.assertIn("do not invent", msg.lower())

    def test_rejects_rounded_or_wrong_booking_time(self) -> None:
        start, end, _, _ = sample_slot_times()
        wrong_start = start.replace(minute=0)  # 11:00 when caller heard 11:30
        wrong_end = end.replace(minute=0)

        self.assertIsNone(
            resolve_offered_slot(
                wrong_start.astimezone(UTC),
                wrong_end.astimezone(UTC),
                sample_offered_slots(),
            )
        )

    def test_accepts_exact_offered_slot_utc(self) -> None:
        start, end, _, _ = sample_slot_times()
        resolved = resolve_offered_slot(
            start.astimezone(UTC),
            end.astimezone(UTC),
            sample_offered_slots(),
        )
        self.assertIsNotNone(resolved)
        resolved_start, resolved_end = resolved
        self.assertEqual(resolved_start, start.astimezone(UTC))
        self.assertEqual(resolved_end, end.astimezone(UTC))

    def test_accepts_second_offered_slot(self) -> None:
        _, _, start, end = sample_slot_times()
        resolved = resolve_offered_slot(
            start.astimezone(UTC),
            end.astimezone(UTC),
            sample_offered_slots(),
        )
        self.assertIsNotNone(resolved)


if __name__ == "__main__":
    unittest.main()
