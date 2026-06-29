"""Date helpers for the AI receptionist — resolves relative dates in business timezone."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo


def business_now(timezone: str) -> datetime:
    return datetime.now(UTC).astimezone(ZoneInfo(timezone))


def resolve_target_date(date_input: str, timezone: str) -> date | None:
    """Parse YYYY-MM-DD or relative terms like 'today' / 'tomorrow' in business timezone."""
    normalized = date_input.strip().lower()
    today = business_now(timezone).date()

    relative_offsets = {
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
    }
    if normalized in relative_offsets:
        return today + timedelta(days=relative_offsets[normalized])

    try:
        return date.fromisoformat(date_input.strip())
    except ValueError:
        return None


def format_date_context(timezone: str) -> str:
    """Human-readable current date context for the system prompt."""
    now = business_now(timezone)
    today = now.date()
    tomorrow = today + timedelta(days=1)

    return (
        f"- Current local time: {now.strftime('%A, %B %d, %Y at %I:%M %p')} ({timezone})\n"
        f"- Today's date: {today.isoformat()}\n"
        f"- Tomorrow's date: {tomorrow.isoformat()}\n"
        f"- When the caller says 'today', use {today.isoformat()}. "
        f"When they say 'tomorrow', use {tomorrow.isoformat()}."
    )
