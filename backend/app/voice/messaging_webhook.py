"""Parse Telnyx Messaging API webhook payloads."""

import json
import logging
from typing import Any

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.voice.webhook_auth import verify_telnyx_webhook_signature

logger = logging.getLogger(__name__)


async def parse_inbound_sms_event(request: Request) -> dict[str, str] | None:
    """
    Validate Telnyx messaging webhook and extract inbound SMS fields.
    Returns None for non-message events (still valid webhook).
    """
    settings = get_settings()
    body = await request.body()

    timestamp = request.headers.get("telnyx-timestamp", "")
    signature = request.headers.get("telnyx-signature-ed25519", "")
    webhook_id = request.headers.get("webhook-id") or request.headers.get("telnyx-webhook-id")

    if signature and timestamp and settings.telnyx_public_key:
        if not verify_telnyx_webhook_signature(
            body,
            timestamp,
            signature,
            settings.telnyx_public_key,
            webhook_id=webhook_id,
        ):
            logger.warning("Invalid Telnyx messaging webhook signature")
            if not settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook signature",
                )

    if not body:
        return None

    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Non-JSON Telnyx messaging webhook body")
        return None

    data = payload.get("data") or {}
    event_type = data.get("event_type") or payload.get("event_type")
    if event_type != "message.received":
        return None

    message = data.get("payload") or {}
    text = (message.get("text") or "").strip()
    from_obj = message.get("from") or {}
    to_list = message.get("to") or []
    to_obj = to_list[0] if to_list else {}

    from_number = from_obj.get("phone_number") or from_obj.get("number") or ""
    to_number = to_obj.get("phone_number") or to_obj.get("number") or ""

    if not from_number or not to_number or not text:
        logger.info("Inbound SMS event missing fields", extra={"event_type": event_type})
        return None

    return {"from": from_number, "to": to_number, "text": text}


def parse_telnyx_sms_payload(payload: dict[str, Any]) -> dict[str, str] | None:
    """Normalize a parsed Telnyx messaging webhook dict (for provider adapters)."""
    data = payload.get("data") or payload
    event_type = data.get("event_type") or payload.get("event_type")
    if event_type != "message.received":
        return None

    message = data.get("payload") or data
    text = (message.get("text") or "").strip()
    from_obj = message.get("from") or {}
    to_list = message.get("to") or []
    to_obj = to_list[0] if to_list else {}

    from_number = from_obj.get("phone_number") or from_obj.get("number") or ""
    to_number = to_obj.get("phone_number") or to_obj.get("number") or ""

    if not from_number or not to_number or not text:
        return None
    return {"from": from_number, "to": to_number, "text": text}
