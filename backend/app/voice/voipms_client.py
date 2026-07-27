"""VoIP.ms REST API client — SMS, DID provisioning, and SIP routing."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

VOIPMS_API_URL = "https://voip.ms/api/v1/rest.php"


def is_voipms_configured() -> bool:
    settings = get_settings()
    return bool(settings.voipms_api_username and settings.voipms_api_password)


def is_phone_provisioning_configured() -> bool:
    return is_voipms_configured()


def is_outbound_call_configured() -> bool:
    # VoIP.ms voice is SIP/account routed — no REST click-to-call for AI gather.
    return False


def _call(method: str, **params: Any) -> dict[str, Any]:
    settings = get_settings()
    if not is_voipms_configured():
        raise RuntimeError("VoIP.ms is not configured")
    query = {
        "api_username": settings.voipms_api_username,
        "api_password": settings.voipms_api_password,
        "method": method,
        **{k: v for k, v in params.items() if v is not None},
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.get(VOIPMS_API_URL, params=query)
        response.raise_for_status()
        data = response.json()
    status = str(data.get("status", "")).lower()
    if status and status not in ("success", "ok"):
        raise RuntimeError(f"VoIP.ms {method} failed: {data.get('status')}")
    return data


def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    settings = get_settings()
    did = _digits(from_number or settings.voipms_did or settings.voipms_phone_number)
    dst = _digits(to_number)
    data = _call("sendSMS", did=did, dst=dst, message=text)
    message_id = str(data.get("sms") or data.get("id") or "")
    logger.info("SMS sent via VoIP.ms", extra={"message_id": message_id, "to": to_number})
    return {"id": message_id, "raw": data}


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    del number_type
    country = country_code.upper().strip()
    results: list[dict[str, Any]] = []
    if country == "CA":
        data = _call("getDIDsCAN", province=prefix or "ON")
        rows = data.get("dids") or data.get("DID") or []
    else:
        # getDIDsUSA requires state; treat short numeric prefix as NPA when possible.
        state = "NY"
        ratecenter = None
        if prefix and prefix.isalpha() and len(prefix) == 2:
            state = prefix.upper()
        data = _call("getDIDsUSA", state=state, ratecenter=ratecenter)
        rows = data.get("dids") or data.get("DID") or []

    if isinstance(rows, dict):
        rows = list(rows.values())
    for item in rows[: min(max(limit, 1), 25)]:
        if not isinstance(item, dict):
            continue
        did = item.get("did") or item.get("number")
        if not did:
            continue
        if prefix and prefix.isdigit() and not str(did).startswith(prefix):
            continue
        phone = did if str(did).startswith("+") else f"+1{str(did).lstrip('1')}" if len(str(did)) == 10 else f"+{did}"
        results.append(
            {
                "phone_number": phone if phone.startswith("+") else f"+{phone}",
                "region": item.get("ratecenter") or item.get("state") or country,
                "cost": item.get("monthly") or item.get("setup"),
            }
        )
    return results


def create_number_order(phone_number: str) -> dict[str, Any]:
    settings = get_settings()
    did = _digits(phone_number)
    routing = settings.voipms_routing or "account"
    data = _call(
        "orderDID",
        did=did,
        routing=routing,
        pop=1,
        dialtime=60,
        cnam=0,
        billing_type=1,
        test=0,
    )
    return {
        "id": did,
        "status": "success",
        "phone_number": phone_number if phone_number.startswith("+") else f"+1{did}",
        "raw": data,
    }


def get_number_order(order_id: str) -> dict[str, Any]:
    record = find_phone_number_record(f"+1{order_id.lstrip('+1')}")
    if not record:
        return {"id": order_id, "status": "pending"}
    return {
        "id": order_id,
        "status": "success",
        "phone_number": record.get("phone_number"),
        "raw": record,
    }


def wait_for_number_order(order_id: str, *, timeout_seconds: int = 45) -> dict[str, Any]:
    del timeout_seconds
    # VoIP.ms orderDID is synchronous.
    return get_number_order(order_id)


def find_phone_number_record(phone_number: str) -> dict[str, Any] | None:
    did = _digits(phone_number)
    data = _call("getDIDsInfo", did=did)
    rows = data.get("dids") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    for item in rows:
        if not isinstance(item, dict):
            continue
        item_did = str(item.get("did") or "")
        if item_did == did or item_did.endswith(did):
            return {
                "id": item_did,
                "phone_number": f"+1{item_did}" if len(item_did) == 10 else f"+{item_did}",
                "raw": item,
            }
    return None


def configure_phone_number(phone_number_id: str, *, sms_url: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    did = _digits(phone_number_id)
    callback = sms_url or f"{settings.public_api_url.rstrip('/')}/api/v1/sms/inbound"
    sms_result = _call(
        "setSMS",
        did=did,
        enable=1,
        url_callback_enable=1,
        url_callback_retry=1,
        url_callback=callback,
    )
    if settings.voipms_routing:
        _call("setDIDRouting", did=did, routing=settings.voipms_routing)
    return sms_result


def release_phone_number(phone_number_id: str) -> None:
    did = _digits(phone_number_id)
    _call("cancelDID", did=did)
    logger.info("VoIP.ms number released", extra={"did": did})


def set_did_routing(phone_number_id: str, routing: str) -> dict[str, Any]:
    return _call("setDIDRouting", did=_digits(phone_number_id), routing=routing)


def _digits(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits
