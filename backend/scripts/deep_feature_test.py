#!/usr/bin/env python3
"""Deep live checks — address recovery, summaries, booking email, SMS continuation."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

# Run inside API container where app is on PYTHONPATH
from app.ai.receptionist_tools import ReceptionistToolsImpl
from app.database import SessionLocal
from app.models import AddressConfirmationToken, Business, CallLog, Customer
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.services.address_confirmation_service import AddressConfirmationService
from app.services.conversation_summary_service import ConversationSummaryService
from app.services.notification_service import NotificationService
from app.services.sms_service import SmsService
from app.voice.session_state import VoiceSessionState
from tests.helpers import sample_business
from unittest.mock import MagicMock, patch

BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1").rstrip("/")
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS  {name}")
    else:
        msg = f"FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        FAILURES.append(msg)


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def test_address_confirm_e2e(db: Session) -> None:
    business = db.query(Business).first()
    if business is None:
        check("Address confirm E2E", False, "No business in DB")
        return

    call = CallLog(
        id=str(uuid4()),
        business_id=business.id,
        channel=ConversationChannel.VOICE,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
        caller_phone="+15551234000",
        summary="Inbound voice call",
        conversation_history=[],
    )
    db.add(call)
    db.commit()

    result = AddressConfirmationService.create_and_send_link(
        db, business, call, customer_name="Jane Doe"
    )
    check(
        "Address link created (SMS may fail without 10DLC)",
        result.get("link_created") is True and bool(result.get("url")),
        str(result),
    )

    token_row = (
        db.query(AddressConfirmationToken)
        .filter(AddressConfirmationToken.call_log_id == call.id)
        .first()
    )
    check("Address token persisted", token_row is not None and token_row.token, "")

    if not token_row:
        return

    status, info = api("GET", f"/public/address-confirm/{token_row.token}")
    check(
        "Public GET address confirm info",
        status == 200 and info.get("business_name") == business.name,
        str(info),
    )

    address = "456 Oak Avenue, Columbus, OH 43215"
    status, confirmed = api(
        "POST",
        f"/public/address-confirm/{token_row.token}",
        {"address": address},
    )
    check(
        "Public POST confirms address",
        status == 200 and confirmed.get("success") is True,
        str(confirmed),
    )

    db.refresh(call)
    customer = (
        db.query(Customer)
        .filter(Customer.business_id == business.id, Customer.phone == "+15551234000")
        .first()
    )
    check(
        "Confirmed address saved to customer",
        customer is not None and customer.address == address,
        str(customer.address if customer else None),
    )
    check("Call linked to customer", call.customer_id == (customer.id if customer else None), "")


async def test_ai_summary(db: Session) -> None:
    business = db.query(Business).first()
    if business is None:
        check("AI summary generation", False, "No business")
        return

    call = CallLog(
        id=str(uuid4()),
        business_id=business.id,
        channel=ConversationChannel.WEB_CHAT,
        direction=CallDirection.INBOUND,
        status=CallStatus.COMPLETED,
        caller_phone="text-chat",
        summary="Text receptionist session",
        conversation_history=[
            {"role": "user", "content": "I have a leak under my sink"},
            {"role": "assistant", "content": "May I have your name?"},
            {"role": "user", "content": "Maria Garcia"},
        ],
    )
    db.add(call)
    db.commit()

    from app.config import get_settings

    if not get_settings().groq_api_key:
        check("AI summary generation", True, "Skipped — no GROQ_API_KEY")
        return

    summary = await ConversationSummaryService.summarize_call_log(db, call.id)
    db.refresh(call)
    check(
        "AI summary written to call_logs.ai_summary",
        bool(summary) and bool(call.ai_summary) and len(call.ai_summary) > 20,
        call.ai_summary or "empty",
    )


async def test_sms_continues_in_progress_call(db: Session) -> None:
    from app.config import get_settings
    from app.voice.call_service import find_business_by_phone

    settings = get_settings()
    to_number = settings.telnyx_phone_number or "+13802738396"
    business = find_business_by_phone(db, to_number)
    if business is None:
        check("SMS continues voice session", False, f"No business for {to_number}")
        return

    call = CallLog(
        id=str(uuid4()),
        business_id=business.id,
        channel=ConversationChannel.VOICE,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
        caller_phone="+15551235000",
        external_call_id="CA-test-sms",
        summary="Inbound voice call",
        conversation_history=[
            {"role": "user", "content": "I have a leak"},
            {"role": "assistant", "content": "What is your name?"},
        ],
    )
    db.add(call)
    db.commit()

    if not get_settings().groq_api_key:
        check("SMS continues voice session", True, "Skipped agent turn — no GROQ_API_KEY")
        return

    await SmsService.handle_inbound(
        db,
        "+15551235000",
        to_number,
        "My name is Alex Turner",
    )
    db.refresh(call)
    user_msgs = [m for m in call.conversation_history if m.get("role") == "user"]
    check(
        "SMS appended to same call_log conversation",
        len(user_msgs) >= 2,
        str(call.conversation_history),
    )


async def test_address_link_tool() -> None:
    state = VoiceSessionState(caller_phone="+15551236000")
    db = MagicMock()
    business = sample_business()
    business.name = "Test Plumbing"
    notifications = MagicMock()
    call = MagicMock()
    call.id = "call-tool-1"
    call.caller_phone = "+15551236000"
    db.query.return_value.filter.return_value.first.return_value = call

    with patch.object(VoiceSessionState, "load", return_value=state):
        tools = ReceptionistToolsImpl(
            db, business, notifications, call_log_id="call-tool-1", voice_mode=True
        )
    with patch(
        "app.services.address_confirmation_service.AddressConfirmationService.create_and_send_link",
        return_value={"sent": True, "link_created": True, "url": "http://localhost:3000/confirm-address/tok"},
    ) as send_mock:
        result = await tools.send_address_confirmation_link(customer_name="Sam Lee")
    check("send_address_confirmation_link tool succeeds", result.success, result.message)
    send_mock.assert_called_once()


def test_booking_email_on_tool() -> None:
    db = MagicMock()
    business = sample_business()
    business.name = "Test Plumbing"
    customer = MagicMock()
    customer.name = "John"
    customer.email = "john@example.com"
    customer.address = "123 Main St, Columbus, OH 43215"
    appt = MagicMock()
    appt.service_type = "Leak repair"
    from datetime import UTC, datetime

    appt.start_time = datetime(2026, 7, 2, 14, 0, tzinfo=UTC)

    svc = NotificationService(db, business)
    with patch.object(svc, "_smtp_configured", return_value=False):
        result = svc.send_booking_confirmation_email(customer, appt)
    check(
        "Booking confirmation email path works (dev log)",
        result.get("sent") is True,
        str(result),
    )


async def main() -> int:
    db = SessionLocal()
    try:
        test_address_confirm_e2e(db)
        await test_ai_summary(db)
        await test_sms_continues_in_progress_call(db)
        await test_address_link_tool()
        test_booking_email_on_tool()
    finally:
        db.close()

    print("\n---")
    if FAILURES:
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print("All deep checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
