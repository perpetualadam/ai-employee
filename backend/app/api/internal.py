"""Internal cron endpoints — protected by CRON_SECRET."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security_policy import verify_internal_secret
from app.database import get_db
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/reminders/run")
def run_reminders(
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_secret),
) -> dict:
    """Send due appointment reminders. Call hourly from cron or scheduler service."""
    result = ReminderService.run_due_reminders(db)
    logger.info(
        "Reminder cron completed",
        extra={"checked": result["checked"], "sent": result["sent"]},
    )
    return result
