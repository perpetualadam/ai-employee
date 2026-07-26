"""Telnyx REST API client — SMS, TeXML call control, and number provisioning."""

import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TELNYX_API_BASE = "https://api.telnyx.com/v2"


def is_telnyx_configured() -> bool:
    settings = get_settings()
    return bool(settings.telnyx_api_key)


def is_phone_provisioning_configured() -> bool:
    settings = get_settings()
    return bool(settings.telnyx_api_key and settings.telnyx_texml_connection_id)


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.telnyx_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, f"{TELNYX_API_BASE}{path}", headers=_headers(), **kwargs)
        response.raise_for_status()
        return response.json()


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

    data = _request("POST", "/messages", json=payload)
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


def playback_stop(call_control_id: str) -> None:
    """Stop Call Control playback — used for duplex barge-in."""
    if not call_control_id:
        return
    _request("POST", f"/calls/{call_control_id}/actions/playback_stop")
    logger.info("Telnyx playback stopped", extra={"call_control_id": call_control_id})


def is_outbound_call_configured() -> bool:
    settings = get_settings()
    return bool(settings.telnyx_api_key and settings.telnyx_texml_connection_id)


def initiate_call(from_number: str, to_number: str, webhook_url: str) -> dict[str, Any]:
    """Place an outbound call via Telnyx Call Control."""
    settings = get_settings()
    if not is_outbound_call_configured():
        raise RuntimeError("Outbound calling is not configured")

    payload: dict[str, Any] = {
        "connection_id": settings.telnyx_texml_connection_id,
        "to": to_number,
        "from": from_number,
        "webhook_url": webhook_url,
        "webhook_url_method": "POST",
    }
    data = _request("POST", "/calls", json=payload)
    record = data.get("data") or {}
    logger.info(
        "Outbound call initiated",
        extra={"to": to_number, "from": from_number, "call_id": record.get("call_control_id")},
    )
    return {
        "id": record.get("id"),
        "call_control_id": record.get("call_control_id"),
        "raw": data,
    }


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search purchasable numbers with voice + SMS for *any* supported country.

    The correct Telnyx filter key is resolved from the domain
    ``NumberSearchProfile`` for the requested country. UK defaults to
    ``filter[phone_number_type]=mobile`` for SMS-friendly 07 numbers; use
    ``number_type=local`` for geographic numbers with optional locality filter.
    """
    from app.domain.telecom import get_number_search_profile  # avoid circular at module level

    normalised_country = country_code.upper().strip()
    search_profile = get_number_search_profile(normalised_country)
    effective_type = number_type or search_profile.default_phone_number_type

    params: dict[str, str | int] = {
        "filter[country_code]": normalised_country,
        "filter[features]": "voice,sms",
        "filter[limit]": min(max(limit, 1), 25),
    }

    if effective_type:
        params["filter[phone_number_type]"] = effective_type

    if prefix and search_profile.prefix_param is not None:
        # UK mobile inventory is country-wide — locality filter does not apply.
        if not (normalised_country == "GB" and effective_type == "mobile"):
            params[search_profile.prefix_param] = prefix.strip()

    data = _request("GET", "/available_phone_numbers", params=params)
    items = data.get("data") or []
    results: list[dict[str, Any]] = []
    for item in items:
        phone = item.get("phone_number")
        if not phone:
            continue
        region = item.get("region_information") or []
        region_label = None
        if region and isinstance(region, list):
            region_label = region[0].get("region_name") if isinstance(region[0], dict) else None
        cost_info = item.get("cost_information") or {}
        results.append(
            {
                "phone_number": phone,
                "region": region_label,
                "cost": cost_info.get("monthly_cost") or cost_info.get("upfront_cost"),
            }
        )
    return results


def create_number_order(phone_number: str) -> dict[str, Any]:
    """Purchase a phone number."""
    payload = {"phone_numbers": [{"phone_number": phone_number}]}
    data = _request("POST", "/number_orders", json=payload)
    return data.get("data") or {}


def get_number_order(order_id: str) -> dict[str, Any]:
    data = _request("GET", f"/number_orders/{order_id}")
    return data.get("data") or {}


def wait_for_number_order(order_id: str, *, timeout_seconds: int = 45) -> dict[str, Any]:
    """Poll until the number order succeeds or fails."""
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = get_number_order(order_id)
        status = (last.get("status") or "").lower()
        if status in ("success", "completed", "active"):
            return last
        if status in ("failed", "cancelled", "canceled"):
            raise RuntimeError(f"Number order failed: {last.get('status')}")
        time.sleep(2)
    raise TimeoutError(f"Number order {order_id} did not complete in time")


def find_phone_number_record(phone_number: str) -> dict[str, Any] | None:
    data = _request(
        "GET",
        "/phone_numbers",
        params={"filter[phone_number]": phone_number},
    )
    items = data.get("data") or []
    return items[0] if items else None


def configure_phone_number(
    phone_number_id: str,
    *,
    connection_id: str,
    messaging_profile_id: str | None = None,
) -> dict[str, Any]:
    """Assign TeXML connection and optional messaging profile."""
    payload: dict[str, Any] = {"connection_id": connection_id}
    data = _request("PATCH", f"/phone_numbers/{phone_number_id}", json=payload)
    result = data.get("data") or {}

    if messaging_profile_id:
        messaging_payload = {"messaging_profile_id": messaging_profile_id}
        _request(
            "PATCH",
            f"/phone_numbers/{phone_number_id}/messaging",
            json=messaging_payload,
        )
    return result
