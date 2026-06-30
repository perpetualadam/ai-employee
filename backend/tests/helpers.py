"""Shared fixtures for voice receptionist specification tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from app.voice.session_state import VoiceSessionState

NY = ZoneInfo("America/New_York")


def sample_business() -> MagicMock:
    business = MagicMock()
    business.id = "047694b9-6e63-4bbf-b186-280e0e23e968"
    business.timezone = "America/New_York"
    business.working_hours = {
        "monday": {"open": "08:00", "close": "17:00"},
        "tuesday": {"open": "08:00", "close": "17:00"},
        "wednesday": {"open": "08:00", "close": "17:00"},
        "thursday": {"open": "08:00", "close": "17:00"},
        "friday": {"open": "08:00", "close": "17:00"},
        "saturday": {"closed": True},
        "sunday": {"closed": True},
    }
    return business


def sample_slot_times() -> tuple[datetime, datetime, datetime, datetime]:
    """11:30 AM and 2:00 PM America/New_York on 2026-07-01 (Wednesday)."""
    start_a = datetime(2026, 7, 1, 11, 30, tzinfo=NY)
    end_a = datetime(2026, 7, 1, 12, 30, tzinfo=NY)
    start_b = datetime(2026, 7, 1, 14, 0, tzinfo=NY)
    end_b = datetime(2026, 7, 1, 15, 0, tzinfo=NY)
    return start_a, end_a, start_b, end_b


def sample_offered_slots() -> list[dict]:
    start_a, end_a, start_b, end_b = sample_slot_times()
    return [
        {
            "start_time": start_a.isoformat(),
            "end_time": end_a.isoformat(),
            "start_time_utc": start_a.astimezone(UTC).isoformat(),
            "end_time_utc": end_a.astimezone(UTC).isoformat(),
            "spoken_time": "11:30 AM",
        },
        {
            "start_time": start_b.isoformat(),
            "end_time": end_b.isoformat(),
            "start_time_utc": start_b.astimezone(UTC).isoformat(),
            "end_time_utc": end_b.astimezone(UTC).isoformat(),
            "spoken_time": "2 PM",
        },
    ]


def fresh_voice_session(*, caller_phone: str = "+447492046947") -> VoiceSessionState:
    return VoiceSessionState(caller_phone=caller_phone)


def intake_complete_session(customer_id: str = "cust-1") -> VoiceSessionState:
    state = fresh_voice_session()
    state.mark_intake_saved(
        customer_id,
        "123 Main Street, Columbus, OH 43215",
        "Brian Smith",
    )
    return state


def ready_to_book_session(customer_id: str = "cust-1") -> VoiceSessionState:
    """Intake done, slots offered on a prior turn — caller may book now."""
    state = intake_complete_session(customer_id)
    state.record_availability(sample_offered_slots())
    state.prior_availability_check = True
    state.availability_checked_this_turn = False
    return state
