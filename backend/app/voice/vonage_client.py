"""Vonage REST API client — SMS, NCCO call control, and number provisioning."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

VONAGE_VOICE_BASE = "https://api.nexmo.com/v1"
VONAGE_REST_BASE = "https://rest.nexmo.com"
VONAGE_API_BASE = "https://api.nexmo.com"


def is_vonage_configured() -> bool:
    settings = get_settings()
    return bool(settings.vonage_api_key and settings.vonage_api_secret)


def is_phone_provisioning_configured() -> bool:
    return is_vonage_configured()


def is_outbound_call_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.vonage_api_key
        and settings.vonage_api_secret
        and (settings.vonage_application_id or settings.public_api_url)
    )


def _auth() -> tuple[str, str]:
    settings = get_settings()
    if not is_vonage_configured():
        raise RuntimeError("Vonage is not configured")
    return settings.vonage_api_key, settings.vonage_api_secret


def _voice_jwt() -> str | None:
    """Build a short-lived JWT when application credentials are present."""
    settings = get_settings()
    app_id = (settings.vonage_application_id or "").strip()
    private_key = (settings.vonage_private_key or "").strip().replace("\\n", "\n")
    if not app_id or not private_key:
        return None
    try:
        import jwt  # PyJWT via python-jose may differ; prefer PyJWT if installed
    except ImportError:
        try:
            from jose import jwt as jose_jwt  # type: ignore
        except ImportError:
            logger.warning("No JWT library available for Vonage application auth")
            return None
        now = int(time.time())
        payload = {
            "application_id": app_id,
            "iat": now,
            "exp": now + 60 * 5,
            "jti": f"{app_id}-{now}",
        }
        return jose_jwt.encode(payload, private_key, algorithm="RS256")

    now = int(time.time())
    payload = {
        "application_id": app_id,
        "iat": now,
        "exp": now + 60 * 5,
        "jti": f"{app_id}-{now}",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def _voice_headers() -> dict[str, str]:
    token = _voice_jwt()
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    return {"Content-Type": "application/json", "Accept": "application/json"}


def voice_auth_headers() -> dict[str, str]:
    """Public auth headers for Voice API / recording downloads."""
    return _voice_headers()


def _voice_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{VONAGE_VOICE_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers = {**_voice_headers(), **headers}
    auth = None if "Authorization" in headers else _auth()
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, headers=headers, auth=auth, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def _rest_request(method: str, path: str, *, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    query = {"api_key": settings.vonage_api_key, "api_secret": settings.vonage_api_secret}
    if params:
        query.update(params)
    url = f"{VONAGE_REST_BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        if method.upper() == "GET":
            response = client.get(url, params=query)
        else:
            response = client.request(method, url, params=query, data=data or {})
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def _api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{VONAGE_API_BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, auth=_auth(), **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def update_call_ncco(call_uuid: str, ncco: str | list[dict[str, Any]]) -> None:
    """Replace the active NCCO on an in-progress Vonage call."""
    payload = json.loads(ncco) if isinstance(ncco, str) else ncco
    _voice_request("PUT", f"/calls/{call_uuid}", json=payload)
    logger.info("Vonage call updated with NCCO", extra={"call_uuid": call_uuid})


def end_call(call_uuid: str) -> None:
    _voice_request("PUT", f"/calls/{call_uuid}", json={"action": "hangup"})
    logger.info("Vonage call ended", extra={"call_uuid": call_uuid})


def initiate_call(from_number: str, to_number: str, webhook_url: str) -> dict[str, Any]:
    """Place an outbound call that fetches NCCO from webhook_url when answered."""
    if not is_outbound_call_configured():
        raise RuntimeError("Outbound calling is not configured")
    settings = get_settings()
    payload: dict[str, Any] = {
        "to": [{"type": "phone", "number": to_number}],
        "from": {"type": "phone", "number": from_number},
        "answer_url": [webhook_url],
        "answer_method": "POST",
        "event_url": [f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status"],
        "event_method": "POST",
    }
    data = _voice_request("POST", "/calls", json=payload)
    call_uuid = data.get("uuid") or data.get("conversation_uuid") or ""
    logger.info(
        "Outbound call initiated via Vonage",
        extra={"to": to_number, "from": from_number, "call_uuid": call_uuid},
    )
    return {"id": call_uuid, "call_control_id": call_uuid, "raw": data}


def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    settings = get_settings()
    sender = from_number or settings.vonage_phone_number
    data = _rest_request(
        "POST",
        "/sms/json",
        data={
            "from": sender,
            "to": to_number.lstrip("+"),
            "text": text,
            "type": "unicode",
        },
    )
    messages = data.get("messages") or []
    message_id = ""
    if messages and isinstance(messages[0], dict):
        message_id = str(messages[0].get("message-id") or messages[0].get("messageId") or "")
        status = str(messages[0].get("status", ""))
        if status not in ("0", "0.0", ""):
            error_text = messages[0].get("error-text") or messages[0].get("errorText") or status
            raise RuntimeError(f"Vonage SMS failed: {error_text}")
    logger.info("SMS sent via Vonage", extra={"message_id": message_id, "to": to_number})
    return {"id": message_id, "raw": data}


def search_available_phone_numbers(
    country_code: str,
    *,
    prefix: str | None = None,
    limit: int = 10,
    number_type: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "country": country_code.upper().strip(),
        "features": "VOICE,SMS",
        "size": min(max(limit, 1), 25),
    }
    if prefix:
        params["pattern"] = prefix.strip()
        params["search_pattern"] = 1
    if number_type:
        params["type"] = number_type
    data = _rest_request("GET", "/number/search", params=params)
    results: list[dict[str, Any]] = []
    for item in data.get("numbers") or []:
        msisdn = item.get("msisdn")
        if not msisdn:
            continue
        phone = msisdn if str(msisdn).startswith("+") else f"+{msisdn}"
        results.append(
            {
                "phone_number": phone,
                "region": item.get("country") or item.get("type"),
                "cost": item.get("cost"),
            }
        )
    return results


def create_number_order(phone_number: str) -> dict[str, Any]:
    digits = phone_number.lstrip("+")
    # Infer country from E.164 — Vonage buy requires ISO country.
    country = _country_from_e164(phone_number)
    data = _rest_request(
        "POST",
        "/number/buy",
        data={"country": country, "msisdn": digits},
    )
    return {
        "id": digits,
        "status": "success" if str(data.get("error-code", "200")) in ("200", "0") else str(data.get("error-code")),
        "phone_number": phone_number if phone_number.startswith("+") else f"+{digits}",
        "raw": data,
    }


def get_number_order(order_id: str) -> dict[str, Any]:
    # Vonage buy is synchronous; treat msisdn as the order id.
    record = find_phone_number_record(f"+{order_id.lstrip('+')}")
    if not record:
        return {"id": order_id, "status": "pending"}
    return {"id": order_id, "status": "success", "phone_number": record.get("phone_number"), "raw": record}


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
    country = _country_from_e164(phone_number)
    data = _rest_request(
        "GET",
        "/account/numbers",
        params={"country": country, "pattern": digits, "search_pattern": 0},
    )
    for item in data.get("numbers") or []:
        msisdn = str(item.get("msisdn") or "")
        if msisdn.lstrip("+") == digits:
            return {
                "id": msisdn,
                "phone_number": f"+{msisdn.lstrip('+')}",
                "raw": item,
            }
    return None


def configure_phone_number(
    phone_number: str,
    *,
    voice_url: str | None = None,
    sms_url: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    digits = phone_number.lstrip("+")
    country = _country_from_e164(phone_number if phone_number.startswith("+") else f"+{digits}")
    data: dict[str, Any] = {"country": country, "msisdn": digits}
    if sms_url or settings.public_api_url:
        data["moHttpUrl"] = sms_url or f"{settings.public_api_url.rstrip('/')}/api/v1/sms/inbound"
    if settings.vonage_application_id:
        data["voiceCallbackType"] = "app"
        data["voiceCallbackValue"] = settings.vonage_application_id
    elif voice_url:
        data["voiceCallbackType"] = "sip"
        data["voiceCallbackValue"] = voice_url
    data["voiceStatusCallback"] = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status"
    return _rest_request("POST", "/number/update", data=data)


def release_phone_number(phone_number_id: str) -> None:
    digits = phone_number_id.lstrip("+")
    country = _country_from_e164(f"+{digits}")
    _rest_request("POST", "/number/cancel", data={"country": country, "msisdn": digits})
    logger.info("Vonage number released", extra={"msisdn": digits})


def create_application(*, name: str, answer_url: str, event_url: str) -> dict[str, Any]:
    payload = {
        "name": name,
        "capabilities": {
            "voice": {
                "webhooks": {
                    "answer_url": {"address": answer_url, "http_method": "POST"},
                    "event_url": {"address": event_url, "http_method": "POST"},
                }
            },
            "messages": {
                "webhooks": {
                    "inbound_url": {
                        "address": f"{get_settings().public_api_url.rstrip('/')}/api/v1/sms/inbound",
                        "http_method": "POST",
                    },
                    "status_url": {
                        "address": f"{get_settings().public_api_url.rstrip('/')}/api/v1/voice/status",
                        "http_method": "POST",
                    },
                }
            },
        },
    }
    return _api_request("POST", "/v2/applications", json=payload)


def get_application(application_id: str) -> dict[str, Any]:
    return _api_request("GET", f"/v2/applications/{application_id}")


def update_application(application_id: str, *, payload: dict[str, Any]) -> dict[str, Any]:
    return _api_request("PUT", f"/v2/applications/{application_id}", json=payload)


def upload_media(*, file_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{VONAGE_API_BASE}/v3/media",
            auth=_auth(),
            files={"file": (filename, file_bytes, content_type)},
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        location = response.headers.get("Location") or ""
        media_id = location.rstrip("/").split("/")[-1] if location else filename
        return {"id": media_id, "url": f"{VONAGE_API_BASE}/v3/media/{media_id}"}


def get_media_info(media_id: str) -> dict[str, Any]:
    return _api_request("GET", f"/v3/media/{media_id}/info")


def update_media_info(
    media_id: str,
    *,
    public: bool | None = None,
    metadata_primary: str | None = None,
    metadata_secondary: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update media metadata — used to attach docs to a regulatory bundle."""
    data: dict[str, Any] = {}
    if public is not None:
        data["public"] = str(public).lower()
    if metadata_primary is not None:
        data["metadata_primary"] = metadata_primary
    if metadata_secondary is not None:
        data["metadata_secondary"] = metadata_secondary
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    url = f"{VONAGE_API_BASE}/v3/media/{media_id}/info"
    with httpx.Client(timeout=60.0) as client:
        response = client.request("PUT", url, auth=_auth(), data=data)
        response.raise_for_status()
        if response.content:
            return response.json()
    return get_media_info(media_id)


def list_media(*, page_size: int = 100, page_index: int = 0) -> dict[str, Any]:
    return _api_request(
        "GET",
        "/v3/media/",
        params={"page_size": page_size, "page_index": page_index, "order": "descending"},
    )


def create_tfn_registration(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a US/CA Toll-Free Number registration (DRAFT or SUBMITTED)."""
    return _api_request("POST", "/tfn/v1/registrations", json=payload)


def get_tfn_registration(registration_id: str) -> dict[str, Any]:
    return _api_request("GET", f"/tfn/v1/registrations/{registration_id}")


def update_tfn_registration(registration_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _api_request("PATCH", f"/tfn/v1/registrations/{registration_id}", json=payload)


def _country_from_e164(phone_number: str) -> str:
    digits = phone_number.lstrip("+")
    # Minimal prefix map for provisioning flows; override via search country when possible.
    if digits.startswith("1"):
        return "US"
    if digits.startswith("44"):
        return "GB"
    if digits.startswith("61"):
        return "AU"
    if digits.startswith("64"):
        return "NZ"
    return "US"


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    """Back-compat helper used by older call sites."""
    return _voice_request(method, path, **kwargs)
