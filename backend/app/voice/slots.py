"""Appointment slot formatting and validation for voice calls."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def spoken_local_time(dt: datetime) -> str:
    """Human-readable local time for TTS, e.g. '11:30 AM'."""
    hour = dt.strftime("%I").lstrip("0") or "12"
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    if minute == "00":
        return f"{hour} {ampm}"
    return f"{hour}:{minute} {ampm}"


def parse_datetime_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_slots_for_voice(raw_slots: list[dict], tz: ZoneInfo) -> list[dict]:
    formatted: list[dict] = []
    for s in raw_slots:
        local_start = s["start_time"].astimezone(tz)
        local_end = s["end_time"].astimezone(tz)
        formatted.append(
            {
                "start_time": local_start.isoformat(),
                "end_time": local_end.isoformat(),
                "start_time_utc": s["start_time"].isoformat(),
                "end_time_utc": s["end_time"].isoformat(),
                "spoken_time": spoken_local_time(local_start),
            }
        )
    return formatted


def resolve_offered_slot(
    start_time: datetime,
    end_time: datetime,
    offered_slots: list[dict],
) -> tuple[datetime, datetime] | None:
    if not offered_slots:
        return None
    for slot in offered_slots:
        slot_start = parse_datetime_utc(slot["start_time_utc"])
        slot_end = parse_datetime_utc(slot["end_time_utc"])
        start_ok = abs((start_time - slot_start).total_seconds()) < 90
        end_ok = abs((end_time - slot_end).total_seconds()) < 90
        if start_ok and end_ok:
            return slot_start, slot_end
    return None


def voice_availability_message(formatted_slots: list[dict]) -> str:
    offer_slots = formatted_slots[:3]
    spoken_options = ", ".join(s["spoken_time"] for s in offer_slots) if offer_slots else "none"
    return (
        f". Offer ONLY these times aloud: {spoken_options}. "
        "Use each slot's spoken_time when speaking — do not invent other times. "
        "When the caller picks one, book using that slot's start_time_utc and end_time_utc exactly."
    )
