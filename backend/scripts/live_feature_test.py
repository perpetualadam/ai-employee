#!/usr/bin/env python3
"""Live integration checks for inbox, address recovery, and related APIs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1").rstrip("/")
FAILURES: list[str] = []


def req(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS  {name}")
    else:
        msg = f"FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        FAILURES.append(msg)


def main() -> int:
    email = f"feature-test-{uuid4().hex[:8]}@example.com"
    password = "TestPass123!"

    status, reg = req(
        "POST",
        "/auth/register",
        {"email": email, "password": password, "full_name": "Feature Tester"},
    )
    check("Register test user", status in (200, 201) and "access_token" in reg, str(reg))
    if "access_token" not in reg:
        return 1
    token = reg["access_token"]

    status, business = req("GET", "/business", token=token)
    slug = business.get("public_slug") if status == 200 else None

    status, chat = req(
        "POST",
        "/receptionist/chat",
        {"message": "I have no hot water", "history": [], "caller_phone": "+15551230001"},
        token=token,
    )
    check("Text receptionist starts session", status == 200 and chat.get("session_id"), str(chat))
    session_id = chat.get("session_id")

    status, chat2 = req(
        "POST",
        "/receptionist/chat",
        {
            "message": "John Smith",
            "history": [
                {"role": "user", "content": "I have no hot water"},
                {"role": "assistant", "content": chat.get("reply", "")},
            ],
            "session_id": session_id,
            "caller_phone": "+15551230001",
        },
        token=token,
    )
    check("Text receptionist turn 2 (name)", status == 200, str(chat2))

    status, conversations = req("GET", "/conversations", token=token)
    check(
        "List conversations inbox",
        status == 200 and isinstance(conversations, list) and len(conversations) >= 1,
        str(conversations)[:300],
    )

    if conversations:
        conv_id = conversations[0]["id"]
        status, detail = req("GET", f"/conversations/{conv_id}", token=token)
        check(
            "Conversation detail with transcript",
            status == 200
            and "messages" in detail
            and "lead_card" in detail
            and len(detail["messages"]) >= 1,
            str(detail)[:300],
        )
        check(
            "Lead card present on detail",
            detail.get("lead_card") is not None,
            str(detail.get("lead_card")),
        )

    # Public address confirm — invalid token should 404
    status, _ = req("GET", "/public/address-confirm/not-a-real-token", token=None)
    check("Invalid address token returns 404", status == 404, str(status))

    # SMS inbound — should accept webhook and return 200
    sms_payload = {
        "data": {
            "event_type": "message.received",
            "payload": {
                "from": {"phone_number": "+15551230001"},
                "to": [{"phone_number": "+13802738396"}],
                "text": "Hello",
            },
        }
    }
    sms_req = urllib.request.Request(
        f"{BASE}/sms/inbound",
        data=json.dumps(sms_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(sms_req, timeout=15) as resp:
            check("Inbound SMS webhook accepts payload", resp.status == 200, str(resp.status))
    except urllib.error.HTTPError as exc:
        check("Inbound SMS webhook accepts payload", False, f"HTTP {exc.code}")

    # Public customer chat (no auth)
    if slug:
        status, chat_info = req("GET", f"/public/chat/{slug}", token=None)
        check(
            "Public chat info",
            status == 200 and chat_info.get("business_name"),
            str(chat_info),
        )
        status, pub = req(
            "POST",
            f"/public/chat/{slug}",
            {"message": "I have a leak under my sink", "history": []},
            token=None,
        )
        check("Public customer chat", status == 200 and pub.get("session_id"), str(pub))
    else:
        check("Public chat slug on business", False, str(business))

    print("\n---")
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print("All live checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
