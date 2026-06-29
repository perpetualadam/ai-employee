"""Telnyx REST API client — SMS and TeXML call control."""

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TELNYX_API_BASE = "https://api.telnyx.com/v2"


def is_telnyx_configured() -> bool:
    settings = get_settings()
    return bool(settings.telnyx_api_key)


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.telnyx_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    """Send an SMS via Telnyx Messaging API."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "from": from_number,
        "to": to_number,
        "text": text,
    }
    if settings.telnyx_messaging_profile_id:
        payload["messaging_profile_id"] = settings.telnyx_messaging_profile_id

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{TELNYX_API_BASE}/messages",
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        message_id = data.get("data", {}).get("id", "")
        logger.info("SMS sent via Telnyx", extra={"message_id": message_id, "to": to_number})
        return {"id": message_id, "raw": data}


def update_call_texml(call_sid: str, texml: str) -> None:
    """Push new TeXML instructions to an active call."""
    settings = get_settings()
    account_sid = settings.telnyx_account_sid
    if not account_sid:
        raise RuntimeError("TELNYX_ACCOUNT_SID is not configured")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{TELNYX_API_BASE}/texml/Accounts/{account_sid}/Calls/{call_sid}",
            headers={
                "Authorization": f"Bearer {settings.telnyx_api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"Texml": texml},
        )
        response.raise_for_status()
        logger.info("Telnyx call updated with TeXML", extra={"call_sid": call_sid})
