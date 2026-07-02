"""Telnyx inbound SMS webhook — recovery/continuation for active voice sessions."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.sms_service import SmsService
from app.integrations.registry import get_sms_inbound_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sms", tags=["sms"])


async def _process_inbound_sms(from_number: str, to_number: str, text: str) -> None:
    db = SessionLocal()
    try:
        await SmsService.handle_inbound(db, from_number, to_number, text)
    finally:
        db.close()


@router.post("/inbound")
async def inbound_sms(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Telnyx Messaging Profile webhook for message.received events.
    Handles SMS recovery/continuation — not a standalone text receptionist.
    """
    event = await get_sms_inbound_adapter().parse_inbound(request)
    if event is None:
        return Response(status_code=200)

    logger.info(
        "Inbound SMS",
        extra={"from": event["from"], "to": event["to"], "text_len": len(event["text"])},
    )
    background_tasks.add_task(
        _process_inbound_sms,
        event["from"],
        event["to"],
        event["text"],
    )
    return Response(status_code=200)
