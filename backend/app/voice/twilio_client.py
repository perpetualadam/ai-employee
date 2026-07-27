"""Twilio REST API client — SMS, TwiML call control, and number provisioning."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
TWILIO_NUMBERS_BASE = "https://numbers.twilio.com/v2"


def is_twilio_configured() -> bool:
    settings = get_settings()
    return bool(settings.twilio_account_sid and settings.twilio_auth_token)


def is_phone_provisioning_configured() -> bool:
    return is_twilio_configured()


def is_outbound_call_configured() -> bool:
    return is_twilio_configured()


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_twilio_configured():
        raise RuntimeError("Twilio is not configured")
    return settings.twilio_account_sid, settings.twilio_auth_token


def _account_url(path: str) -> str:
    settings = get_settings()
    return f"{TWILIO_API_BASE}/Accounts/{settings.twilio_account_sid}{path}"


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = _account_url(path)
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, auth=_auth(), **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def _numbers_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{TWILIO_NUMBERS_BASE}{path}"
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
    """Send an SMS via Twilio Messages API."""
    settings = get_settings()
    data: dict[str, str] = {"To": to_number, "Body": text}
    if settings.twilio_messaging_service_sid:
        data["MessagingServiceSid"] = settings.twilio_messaging_service_sid
    else:
        data["From"] = from_number

    result = _request("POST", "/Messages.json", data=data)
    message_id = result.get("sid", "")
    logger.info("SMS sent via Twilio", extra={"message_id": message_id, "to": to_number})
    return {"id": message_id, "raw": result}


def update_call_twiml(call_sid: str, twiml: str) -> None:
    """Push new TwiML to an in-progress call."""
    _request("POST", f"/Calls/{call_sid}.json", data={"Twiml": twiml})
    logger.info("Twilio call updated with TwiML", extra={"call_sid": call_sid})


def end_call(call_sid: str) -> None:
    """Hang up an in-progress call via REST."""
    _request("POST", f"/Calls/{call_sid}.json", data={"Status": "completed"})
    logger.info("Twilio call ended", extra={"call_sid": call_sid})


def initiate_call(from_number: str, to_number: str, webhook_url: str) -> dict[str, Any]:
    """Place an outbound call that fetches TwiML from webhook_url when answered."""
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
        "Outbound call initiated via Twilio",
        extra={"to": to_number, "from": from_number, "call_sid": call_sid},
    )
    return {"id": call_sid, "call_control_id": call_sid, "raw": result}


def _available_number_type(number_type: str | None) -> str:
    normalized = (number_type or "local").strip().lower()
    if normalized in ("mobile", "local", "tollfree", "toll_free"):
        return "TollFree" if normalized in ("tollfree", "toll_free") else normalized.capitalize()
    return "Local"


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search purchasable Twilio numbers with voice + SMS."""
    from app.domain.telecom import get_number_search_profile

    normalised_country = country_code.upper().strip()
    search_profile = get_number_search_profile(normalised_country)
    effective_type = number_type or search_profile.default_phone_number_type or "local"
    path_type = _available_number_type(effective_type)

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

    path = f"/AvailablePhoneNumbers/{normalised_country}/{path_type}.json"
    try:
        data = _request("GET", path, params=params)
    except httpx.HTTPStatusError:
        # Fall back to Local inventory when Mobile/TollFree is unavailable.
        if path_type != "Local":
            data = _request(
                "GET",
                f"/AvailablePhoneNumbers/{normalised_country}/Local.json",
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
    """Purchase a phone number (Twilio IncomingPhoneNumbers create)."""
    data: dict[str, str] = {
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
    """Twilio purchases are synchronous — treat the SID as a completed order."""
    result = _request("GET", f"/IncomingPhoneNumbers/{order_id}.json")
    return {
        "id": result.get("sid") or order_id,
        "status": "success",
        "phone_number": result.get("phone_number"),
        "raw": result,
    }


def wait_for_number_order(order_id: str, *, timeout_seconds: int = 45) -> dict[str, Any]:
    """Poll until the purchased number record is readable."""
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
    return {
        "id": item.get("sid"),
        "phone_number": item.get("phone_number"),
        "raw": item,
    }


def configure_phone_number(
    phone_number_id: str,
    *,
    voice_url: str | None = None,
    sms_url: str | None = None,
    messaging_service_sid: str | None = None,
) -> dict[str, Any]:
    """Assign voice/SMS webhooks (and optional Messaging Service) on a Twilio number."""
    data: dict[str, str] = {}
    if voice_url:
        data["VoiceUrl"] = voice_url
        data["VoiceMethod"] = "POST"
    if sms_url:
        data["SmsUrl"] = sms_url
        data["SmsMethod"] = "POST"
    if messaging_service_sid:
        # Messaging Service assignment uses a separate resource; keep webhook for inbound.
        data["SmsApplicationSid"] = ""
    if not data:
        data = {
            "VoiceUrl": _voice_webhook_url(),
            "VoiceMethod": "POST",
            "SmsUrl": _sms_webhook_url(),
            "SmsMethod": "POST",
        }
    result = _request("POST", f"/IncomingPhoneNumbers/{phone_number_id}.json", data=data)
    if messaging_service_sid:
        logger.info(
            "Twilio number configured; messaging service sid provided",
            extra={"phone_number_id": phone_number_id, "messaging_service_sid": messaging_service_sid},
        )
    return result


def release_phone_number(phone_number_id: str) -> None:
    _request("DELETE", f"/IncomingPhoneNumbers/{phone_number_id}.json")
    logger.info("Twilio number released", extra={"phone_number_id": phone_number_id})


def create_end_user(*, friendly_name: str, end_user_type: str, attributes: dict[str, Any]) -> dict[str, Any]:
    return _numbers_request(
        "POST",
        "/RegulatoryCompliance/EndUsers",
        data={
            "FriendlyName": friendly_name,
            "Type": end_user_type,
            "Attributes": json.dumps(attributes),
        },
    )


def upload_supporting_document(
    *,
    friendly_name: str,
    document_type: str,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, str] = {
        "FriendlyName": friendly_name,
        "Type": document_type,
    }
    if attributes:
        data["Attributes"] = json.dumps(attributes)
    return _numbers_request("POST", "/RegulatoryCompliance/SupportingDocuments", data=data)


def create_regulatory_bundle(
    *,
    friendly_name: str,
    email: str,
    iso_country: str,
    end_user_type: str,
    number_type: str = "local",
) -> dict[str, Any]:
    return _numbers_request(
        "POST",
        "/RegulatoryCompliance/Bundles",
        data={
            "FriendlyName": friendly_name,
            "Email": email,
            "IsoCountry": iso_country,
            "EndUserType": end_user_type,
            "NumberType": number_type,
        },
    )


def assign_bundle_item(*, bundle_sid: str, object_sid: str) -> dict[str, Any]:
    return _numbers_request(
        "POST",
        f"/RegulatoryCompliance/Bundles/{bundle_sid}/ItemAssignments",
        data={"ObjectSid": object_sid},
    )


def submit_regulatory_bundle(bundle_sid: str) -> dict[str, Any]:
    return _numbers_request(
        "POST",
        f"/RegulatoryCompliance/Bundles/{bundle_sid}",
        data={"Status": "pending-review"},
    )


def get_regulatory_bundle(bundle_sid: str) -> dict[str, Any]:
    return _numbers_request("GET", f"/RegulatoryCompliance/Bundles/{bundle_sid}")


def get_end_user(end_user_sid: str) -> dict[str, Any]:
    return _numbers_request("GET", f"/RegulatoryCompliance/EndUsers/{end_user_sid}")
