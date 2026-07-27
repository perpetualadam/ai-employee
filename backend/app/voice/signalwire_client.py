"""SignalWire Compatibility API client — cXML voice, SMS, numbers (Twilio-compatible)."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def is_signalwire_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.signalwire_project_id
        and settings.signalwire_api_token
        and settings.signalwire_space_url
    )


def is_phone_provisioning_configured() -> bool:
    return is_signalwire_configured()


def is_outbound_call_configured() -> bool:
    return is_signalwire_configured()


def _space_host() -> str:
    settings = get_settings()
    raw = (settings.signalwire_space_url or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return urlparse(raw).netloc or raw
    return raw.rstrip("/")


def _api_base() -> str:
    return f"https://{_space_host()}/api/laml/2010-04-01"


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_signalwire_configured():
        raise RuntimeError("SignalWire is not configured")
    return settings.signalwire_project_id, settings.signalwire_api_token


def _account_url(path: str) -> str:
    settings = get_settings()
    return f"{_api_base()}/Accounts/{settings.signalwire_project_id}{path}"


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = _account_url(path)
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, auth=_auth(), **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def _voice_webhook_url() -> str:
    settings = get_settings()
    return f"{settings.public_api_url.rstrip('/')}/api/v1/voice/inbound"


def _sms_webhook_url() -> str:
    settings = get_settings()
    return f"{settings.public_api_url.rstrip('/')}/api/v1/sms/inbound"


def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    settings = get_settings()
    data = {
        "To": to_number,
        "Body": text,
        "From": from_number or settings.signalwire_phone_number,
    }
    result = _request("POST", "/Messages.json", data=data)
    message_id = result.get("sid", "")
    logger.info("SMS sent via SignalWire", extra={"message_id": message_id, "to": to_number})
    return {"id": message_id, "raw": result}


def update_call_cxml(call_sid: str, cxml: str) -> None:
    _request("POST", f"/Calls/{call_sid}.json", data={"Twiml": cxml})
    logger.info("SignalWire call updated with cXML", extra={"call_sid": call_sid})


def end_call(call_sid: str) -> None:
    _request("POST", f"/Calls/{call_sid}.json", data={"Status": "completed"})
    logger.info("SignalWire call ended", extra={"call_sid": call_sid})


def initiate_call(from_number: str, to_number: str, webhook_url: str) -> dict[str, Any]:
    if not is_outbound_call_configured():
        raise RuntimeError("Outbound calling is not configured")
    result = _request(
        "POST",
        "/Calls.json",
        data={
            "From": from_number,
            "To": to_number,
            "Url": webhook_url,
            "Method": "POST",
        },
    )
    call_sid = result.get("sid", "")
    logger.info(
        "Outbound call initiated via SignalWire",
        extra={"to": to_number, "from": from_number, "call_sid": call_sid},
    )
    return {"id": call_sid, "call_control_id": call_sid, "raw": result}


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    path_type = "Local"
    normalized = (number_type or "local").strip().lower()
    if normalized in ("tollfree", "toll_free"):
        path_type = "TollFree"
    elif normalized == "mobile":
        path_type = "Mobile"
    params: dict[str, str | int] = {
        "PageSize": min(max(limit, 1), 25),
        "VoiceEnabled": "true",
        "SmsEnabled": "true",
    }
    if prefix:
        cleaned = prefix.strip()
        if cleaned.isdigit() and len(cleaned) <= 3 and path_type == "Local":
            params["AreaCode"] = cleaned
        else:
            params["Contains"] = cleaned
    path = f"/AvailablePhoneNumbers/{country_code.upper().strip()}/{path_type}.json"
    try:
        data = _request("GET", path, params=params)
    except httpx.HTTPStatusError:
        if path_type != "Local":
            data = _request(
                "GET",
                f"/AvailablePhoneNumbers/{country_code.upper().strip()}/Local.json",
                params=params,
            )
        else:
            raise
    results: list[dict[str, Any]] = []
    for item in data.get("available_phone_numbers") or []:
        phone = item.get("phone_number")
        if not phone:
            continue
        results.append(
            {
                "phone_number": phone,
                "region": item.get("locality") or item.get("region") or item.get("iso_country"),
                "cost": None,
            }
        )
    return results


def create_number_order(phone_number: str) -> dict[str, Any]:
    data = {
        "PhoneNumber": phone_number,
        "VoiceUrl": _voice_webhook_url(),
        "VoiceMethod": "POST",
        "SmsUrl": _sms_webhook_url(),
        "SmsMethod": "POST",
        "StatusCallback": f"{get_settings().public_api_url.rstrip('/')}/api/v1/voice/status",
        "StatusCallbackMethod": "POST",
    }
    result = _request("POST", "/IncomingPhoneNumbers.json", data=data)
    return {
        "id": result.get("sid"),
        "status": "success",
        "phone_number": result.get("phone_number") or phone_number,
        "raw": result,
    }


def get_number_order(order_id: str) -> dict[str, Any]:
    result = _request("GET", f"/IncomingPhoneNumbers/{order_id}.json")
    return {
        "id": result.get("sid") or order_id,
        "status": "success",
        "phone_number": result.get("phone_number"),
        "raw": result,
    }


def wait_for_number_order(order_id: str, *, timeout_seconds: int = 45) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = get_number_order(order_id)
        if last.get("status") == "success" and last.get("id"):
            return last
        time.sleep(1)
    raise TimeoutError(f"Number order {order_id} did not complete in time")


def find_phone_number_record(phone_number: str) -> dict[str, Any] | None:
    data = _request(
        "GET",
        "/IncomingPhoneNumbers.json",
        params={"PhoneNumber": phone_number, "PageSize": 1},
    )
    items = data.get("incoming_phone_numbers") or []
    if not items:
        return None
    item = items[0]
    return {"id": item.get("sid"), "phone_number": item.get("phone_number"), "raw": item}


def configure_phone_number(
    phone_number_id: str,
    *,
    voice_url: str | None = None,
    sms_url: str | None = None,
) -> dict[str, Any]:
    data: dict[str, str] = {}
    if voice_url:
        data["VoiceUrl"] = voice_url
        data["VoiceMethod"] = "POST"
    if sms_url:
        data["SmsUrl"] = sms_url
        data["SmsMethod"] = "POST"
    if not data:
        data = {
            "VoiceUrl": _voice_webhook_url(),
            "VoiceMethod": "POST",
            "SmsUrl": _sms_webhook_url(),
            "SmsMethod": "POST",
        }
    return _request("POST", f"/IncomingPhoneNumbers/{phone_number_id}.json", data=data)


def release_phone_number(phone_number_id: str) -> None:
    _request("DELETE", f"/IncomingPhoneNumbers/{phone_number_id}.json")
    logger.info("SignalWire number released", extra={"phone_number_id": phone_number_id})


def get_account() -> dict[str, Any]:
    """Fetch the Compatibility API account/project record."""
    settings = get_settings()
    url = f"{_api_base()}/Accounts/{settings.signalwire_project_id}.json"
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, auth=_auth())
        response.raise_for_status()
        return response.json() if response.content else {}
