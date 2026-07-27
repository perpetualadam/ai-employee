"""Plivo REST API client — SMS, PlivoXML call control, and number provisioning."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PLIVO_API_BASE = "https://api.plivo.com/v1"

# Plivo live call updates require an answer URL (no inline XML push like TwiML).
_PLIVO_XML_CACHE: dict[str, str] = {}


def stash_call_xml(call_uuid: str, xml: str) -> None:
    _PLIVO_XML_CACHE[call_uuid] = xml


def pop_call_xml(call_uuid: str) -> str | None:
    return _PLIVO_XML_CACHE.pop(call_uuid, None)


def peek_call_xml(call_uuid: str) -> str | None:
    return _PLIVO_XML_CACHE.get(call_uuid)


def is_plivo_configured() -> bool:
    settings = get_settings()
    return bool(settings.plivo_auth_id and settings.plivo_auth_token)


def is_phone_provisioning_configured() -> bool:
    return is_plivo_configured()


def is_outbound_call_configured() -> bool:
    return is_plivo_configured()


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_plivo_configured():
        raise RuntimeError("Plivo is not configured")
    return settings.plivo_auth_id, settings.plivo_auth_token


def _account_path(path: str) -> str:
    settings = get_settings()
    return f"{PLIVO_API_BASE}/Account/{settings.plivo_auth_id}{path}"


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = _account_path(path)
    headers = kwargs.pop("headers", {})
    headers = {"Content-Type": "application/json", "Accept": "application/json", **headers}
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, auth=_auth(), headers=headers, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "src": from_number or settings.plivo_phone_number,
        "dst": to_number,
        "text": text,
    }
    result = _request("POST", "/Message/", json=payload)
    message_id = result.get("message_uuid") or ""
    if isinstance(message_id, list):
        message_id = message_id[0] if message_id else ""
    logger.info("SMS sent via Plivo", extra={"message_id": message_id, "to": to_number})
    return {"id": str(message_id), "raw": result}


def update_call_xml(call_uuid: str, xml: str) -> None:
    """
    Push new PlivoXML to an in-progress call.

    Plivo transfers the A-leg to an answer URL; we stash XML and serve it from
    ``/api/v1/voice/plivo/xml``.
    """
    settings = get_settings()
    stash_call_xml(call_uuid, xml)
    answer_url = (
        f"{settings.public_api_url.rstrip('/')}/api/v1/voice/plivo/xml"
        f"?call_uuid={call_uuid}"
    )
    _request(
        "POST",
        f"/Call/{call_uuid}/",
        json={"legs": "aleg", "aleg_url": answer_url, "aleg_method": "GET"},
    )
    logger.info("Plivo call updated with XML URL", extra={"call_uuid": call_uuid})


def end_call(call_uuid: str) -> None:
    _request("DELETE", f"/Call/{call_uuid}/")
    logger.info("Plivo call ended", extra={"call_uuid": call_uuid})


def initiate_call(from_number: str, to_number: str, webhook_url: str) -> dict[str, Any]:
    if not is_outbound_call_configured():
        raise RuntimeError("Outbound calling is not configured")
    settings = get_settings()
    result = _request(
        "POST",
        "/Call/",
        json={
            "from": from_number,
            "to": to_number,
            "answer_url": webhook_url,
            "answer_method": "POST",
            "hangup_url": f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status",
            "hangup_method": "POST",
        },
    )
    call_uuid = result.get("request_uuid") or result.get("call_uuid") or ""
    logger.info(
        "Outbound call initiated via Plivo",
        extra={"to": to_number, "from": from_number, "call_uuid": call_uuid},
    )
    return {"id": call_uuid, "call_control_id": call_uuid, "raw": result}


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "country_iso": country_code.upper().strip(),
        "limit": min(max(limit, 1), 20),
        "services": "voice,sms",
    }
    if number_type:
        params["type"] = number_type
    if prefix:
        params["pattern"] = prefix.strip()
    data = _request("GET", "/PhoneNumber/", params=params)
    results: list[dict[str, Any]] = []
    for item in data.get("objects") or []:
        phone = item.get("number")
        if not phone:
            continue
        formatted = phone if str(phone).startswith("+") else f"+{phone}"
        results.append(
            {
                "phone_number": formatted,
                "region": item.get("region") or item.get("city") or item.get("country"),
                "cost": item.get("monthly_rental_rate") or item.get("setup_rate"),
            }
        )
    return results


def create_number_order(phone_number: str) -> dict[str, Any]:
    digits = phone_number.lstrip("+")
    settings = get_settings()
    payload: dict[str, Any] = {}
    if settings.plivo_app_id:
        payload["app_id"] = settings.plivo_app_id
    result = _request("POST", f"/PhoneNumber/{digits}/", json=payload or None)
    number = result.get("numbers") or digits
    if isinstance(number, list):
        number = number[0] if number else digits
    return {
        "id": str(number).lstrip("+"),
        "status": "success",
        "phone_number": phone_number if phone_number.startswith("+") else f"+{digits}",
        "raw": result,
    }


def get_number_order(order_id: str) -> dict[str, Any]:
    record = find_phone_number_record(f"+{order_id.lstrip('+')}")
    if not record:
        return {"id": order_id, "status": "pending"}
    return {
        "id": order_id,
        "status": "success",
        "phone_number": record.get("phone_number"),
        "raw": record,
    }


def wait_for_number_order(order_id: str, *, timeout_seconds: int = 45) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = get_number_order(order_id)
        if last.get("status") == "success":
            return last
        time.sleep(1)
    raise TimeoutError(f"Number order {order_id} did not complete in time")


def find_phone_number_record(phone_number: str) -> dict[str, Any] | None:
    digits = phone_number.lstrip("+")
    try:
        item = _request("GET", f"/Number/{digits}/")
    except httpx.HTTPStatusError:
        return None
    number = item.get("number") or digits
    return {
        "id": str(number).lstrip("+"),
        "phone_number": f"+{str(number).lstrip('+')}",
        "raw": item,
    }


def configure_phone_number(
    phone_number_id: str,
    *,
    app_id: str | None = None,
    alias: str | None = None,
) -> dict[str, Any]:
    digits = phone_number_id.lstrip("+")
    payload: dict[str, Any] = {}
    settings = get_settings()
    effective_app = app_id or settings.plivo_app_id
    if effective_app:
        payload["app_id"] = effective_app
    if alias:
        payload["alias"] = alias
    if not payload:
        payload["alias"] = "ai-employee"
    return _request("POST", f"/Number/{digits}/", json=payload)


def release_phone_number(phone_number_id: str) -> None:
    digits = phone_number_id.lstrip("+")
    _request("DELETE", f"/Number/{digits}/")
    logger.info("Plivo number released", extra={"number": digits})


def create_application(*, app_name: str, answer_url: str, message_url: str) -> dict[str, Any]:
    settings = get_settings()
    return _request(
        "POST",
        "/Application/",
        json={
            "app_name": app_name,
            "answer_url": answer_url,
            "answer_method": "POST",
            "hangup_url": f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status",
            "hangup_method": "POST",
            "message_url": message_url,
            "message_method": "POST",
        },
    )


def get_application(app_id: str) -> dict[str, Any]:
    return _request("GET", f"/Application/{app_id}/")


def create_compliance_application(
    *,
    end_user_type: str,
    country_iso: str,
    number_type: str = "local",
) -> dict[str, Any]:
    return _request(
        "POST",
        "/ComplianceApplication/",
        json={
            "end_user_type": end_user_type,
            "country_iso": country_iso,
            "number_type": number_type,
        },
    )


def get_compliance_application(application_id: str) -> dict[str, Any]:
    return _request("GET", f"/ComplianceApplication/{application_id}/")


def submit_compliance_application(application_id: str) -> dict[str, Any]:
    return _request(
        "POST",
        f"/ComplianceApplication/{application_id}/",
        json={"status": "submitted"},
    )


def create_end_user(*, end_user_type: str, attributes: dict[str, Any]) -> dict[str, Any]:
    return _request(
        "POST",
        "/EndUser/",
        json={"end_user_type": end_user_type, **attributes},
    )


def upload_compliance_document(*, file_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            _account_path("/ComplianceDocument/"),
            auth=_auth(),
            files={"file": (filename, file_bytes, content_type)},
        )
        response.raise_for_status()
        return response.json() if response.content else {"id": filename}
