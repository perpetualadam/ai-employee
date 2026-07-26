"""Vonage Voice REST client — in-call NCCO updates."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

VONAGE_API_BASE = "https://api.nexmo.com/v1"


def is_vonage_configured() -> bool:
    settings = get_settings()
    return bool(settings.vonage_api_key and settings.vonage_api_secret)


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_vonage_configured():
        raise RuntimeError("Vonage is not configured")
    return settings.vonage_api_key, settings.vonage_api_secret


def update_call_ncco(call_uuid: str, ncco: str | list[dict[str, Any]]) -> None:
    """Replace the active NCCO on an in-progress Vonage call."""
    payload = json.loads(ncco) if isinstance(ncco, str) else ncco
    url = f"{VONAGE_API_BASE}/calls/{call_uuid}"
    with httpx.Client(timeout=30.0) as client:
        response = client.put(url, auth=_auth(), json=payload)
        response.raise_for_status()
    logger.info("Vonage call updated with NCCO", extra={"call_uuid": call_uuid})


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{VONAGE_API_BASE}{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.request(method, url, auth=_auth(), **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
