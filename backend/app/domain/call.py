"""Call-log helpers shared across channels."""


def call_has_booking(summary: str | None) -> bool:
    if not summary:
        return False
    return "booked" in summary.lower()
