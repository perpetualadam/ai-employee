"""Telnyx inbound SMS webhook — recovery/continuation for active voice sessions."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.sms_service import SmsService
from app.integrations.registry import get_sms_inbound_adapter_for_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sms", tags=["sms"])


async def _process_inbound_sms(
    from_number: str,
    to_number: str,
    text: str,
    *,
    provider: str,
    external_id: str | None,
) -> None:
    db = SessionLocal()
    try:
        await SmsService.handle_inbound(
            db,
            from_number,
            to_number,
            text,
            provider=provider,
            external_id=external_id,
            raw_payload={
                "from": from_number,
                "to": to_number,
                "text": text,
                "external_id": external_id,
                "provider": provider,
            },
        )
    finally:
        db.close()


@router.api_route("/inbound", methods=["GET", "POST"])
async def inbound_sms(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    CPaaS messaging webhook for inbound SMS (Telnyx/Twilio/Vonage/Plivo/SignalWire/VoIP.ms).
    Handles SMS recovery/continuation — not a standalone text receptionist.
    """
    adapter = get_sms_inbound_adapter_for_request(request)
    event = await adapter.parse_inbound(request)
    if event is None:
        # VoIP.ms URL callback retry expects a plain "ok" body.
        if adapter.provider_name == "voipms":
            return Response(content="ok", media_type="text/plain", status_code=200)
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
        provider=adapter.provider_name,
        external_id=event.get("id") or event.get("external_id"),
    )
    if adapter.provider_name == "voipms":
        return Response(content="ok", media_type="text/plain", status_code=200)
    return Response(status_code=200)
