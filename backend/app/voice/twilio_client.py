"""Twilio REST client — call control isolated from core voice logic."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def is_twilio_configured() -> bool:
    settings = get_settings()
    return bool(settings.twilio_account_sid and settings.twilio_auth_token)


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_twilio_configured():
        raise RuntimeError("Twilio is not configured")
    return settings.twilio_account_sid, settings.twilio_auth_token


def update_call_twiml(call_sid: str, twiml: str) -> None:
    """Push new TwiML to an in-progress call."""
    settings = get_settings()
    url = f"{TWILIO_API_BASE}/Accounts/{settings.twilio_account_sid}/Calls/{call_sid}.json"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            auth=_auth(),
            data={"Twiml": twiml},
        )
        response.raise_for_status()
    logger.info("Twilio call updated with TwiML", extra={"call_sid": call_sid})


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    settings = get_settings()
    url = f"{TWILIO_API_BASE}/Accounts/{settings.twilio_account_sid}{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.request(method, url, auth=_auth(), **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
