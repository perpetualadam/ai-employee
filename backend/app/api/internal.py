"""Internal cron endpoints — protected by CRON_SECRET."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_cron_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.cron_secret:
        if settings.debug:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured.",
        )
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid cron secret")


@router.post("/reminders/run")
def run_reminders(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_cron_secret),
) -> dict:
    """Send due appointment reminders. Call hourly from cron or scheduler service."""
    result = ReminderService.run_due_reminders(db)
    logger.info(
        "Reminder cron completed",
        extra={"checked": result["checked"], "sent": result["sent"]},
    )
    return result
