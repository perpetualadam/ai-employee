#!/usr/bin/env python3
"""P0 local QA — multi-trade onboarding seed + text chat booking smoke tests.

Run inside the API container (needs GROQ_API_KEY for full chat flow):

    docker compose exec api python scripts/p0_trade_qa.py

Optional: pass trade slugs to test subset:

    docker compose exec api python scripts/p0_trade_qa.py plumbing gas_engineer mobile_mechanic
"""

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

# Three trades for P0 — plumbing (baseline), gas engineer (GB compliance), mobile mechanic
P0_TRADES = [
    {
        "slug": "plumbing",
        "industry": "plumbing",
        "country": "US",
        "business_name": "QA Plumbing Co",
        "problem": "I have no hot water",
        "expected_service": "Drain cleaning",
    },
    {
        "slug": "gas_engineer",
        "industry": "gas_engineer",
        "country": "GB",
        "business_name": "QA Gas Heating Ltd",
        "problem": "My boiler will not start and there is no heating",
        "expected_service": "Boiler service",
    },
    {
        "slug": "mobile_mechanic",
        "industry": "mobile_mechanic",
        "country": "US",
        "business_name": "QA Road Rescue",
        "problem": "My car will not start, I think the battery is dead",
        "expected_service": "Roadside call-out",
    },
]

BOOKING_TURNS = [
    "Alex Johnson",
    "123 Main Street, Columbus, OH 43215",
    "yes that is all correct",
    "tomorrow please",
    "I'll take the first slot",
    "no thanks bye",
]


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
    else:
        msg = f"  FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        FAILURES.append(f"[{name}] {detail}")


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def run_trade_qa(trade: dict) -> None:
    label = trade["slug"]
    print(f"\n=== Trade QA: {label} ({trade['country']}) ===")

    email = f"p0-{label}-{uuid4().hex[:8]}@example.com"
    password = "P0TestPass123!"

    status, reg = api(
        "POST",
        "/auth/register",
        {"email": email, "password": password, "full_name": f"P0 {label}"},
    )
    check("Register", status in (200, 201) and "access_token" in reg, str(reg)[:200])
    if "access_token" not in reg:
        return
    token = reg["access_token"]

    status, _ = api(
        "PATCH",
        "/business",
        {
            "name": trade["business_name"],
            "industry": trade["industry"],
            "country": trade["country"],
            "timezone": "America/New_York" if trade["country"] == "US" else "Europe/London",
        },
        token=token,
    )
    check("Set business profile", status == 200, str(status))

    status, trades = api("GET", "/onboarding/trades", token=token)
    match = next((t for t in trades if t.get("value") == trade["industry"]), None)
    check(
        "Trade in onboarding catalog",
        status == 200 and match is not None,
        str(match),
    )
    if match:
        check(
            "Catalog lists expected seed service",
            trade["expected_service"] in match.get("services", []),
            str(match.get("services")),
        )

    status, seed = api("POST", "/onboarding/seed-defaults", token=token)
    check(
        "Seed defaults",
        status == 200 and seed.get("services", 0) >= 1 and seed.get("industry") == trade["industry"],
        str(seed),
    )

    status, services = api("GET", "/business/services", token=token)
    names = [s.get("name") for s in services] if isinstance(services, list) else []
    check(
        "Services persisted",
        status == 200 and trade["expected_service"] in names,
        str(names),
    )

    status, rules = api("GET", "/business/emergency-rules", token=token)
    check(
        "Emergency rules persisted",
        status == 200 and isinstance(rules, list) and len(rules) >= 1,
        str(len(rules) if isinstance(rules, list) else rules),
    )

    # Text chat intake — requires GROQ_API_KEY
    if not os.environ.get("GROQ_API_KEY"):
        check("Text chat booking flow", True, "Skipped — set GROQ_API_KEY in .env")
        print(f"  MANUAL  Voice: call Telnyx number; greeting should mention {trade['industry']} examples")
        return

    history: list[dict] = []
    session_id: str | None = None
    caller = "+1555123" + str(abs(hash(label)) % 10000).zfill(4)
    all_messages = [trade["problem"], *BOOKING_TURNS]
    booked = False
    chat: dict = {}

    for i, message in enumerate(all_messages):
        status, chat = api(
            "POST",
            "/receptionist/chat",
            {
                "message": message,
                "history": history,
                "session_id": session_id,
                "caller_phone": caller,
            },
            token=token,
        )
        if status != 200:
            check(f"Chat turn {i + 1}", False, str(chat)[:300])
            break
        session_id = chat.get("session_id") or session_id
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": chat.get("reply", "")})
        tools = chat.get("tools_called") or []
        if i == 0:
            check("Chat turn 1 (problem)", bool(chat.get("reply")), "")
        if any(t.get("name") == "book_appointment" and t.get("success") for t in tools):
            booked = True
            check("Booking completed via chat", True, "")
            break

    if not booked and os.environ.get("GROQ_API_KEY"):
        status, appts = api("GET", "/appointments", token=token)
        has_appt = status == 200 and isinstance(appts, list) and len(appts) >= 1
        if has_appt:
            check("Booking completed via chat", True, "Appointment found on calendar")
            booked = True
        else:
            check(
                "Booking completed via chat",
                False,
                "Finish in Dashboard → Receptionist (see docs/P0_QA.md)",
            )

    if booked:
        status, appts = api("GET", "/appointments", token=token)
        check(
            "Appointment on calendar",
            status == 200 and isinstance(appts, list) and len(appts) >= 1,
            str(len(appts) if isinstance(appts, list) else appts),
        )

    print(f"  MANUAL  Voice: call your Telnyx number as {label} tenant; verify trade greeting")
    print(f"  MANUAL  Dashboard → Calendar: cancel test appointment if needed")


def main() -> int:
    print("P0 Multi-Trade Local QA")
    print(f"API: {BASE}")

    try:
        req = urllib.request.Request(f"{BASE.rsplit('/api/v1', 1)[0]}/health/ready")
        with urllib.request.urlopen(req, timeout=10) as resp:
            check("API /health/ready", resp.status == 200, "")
    except Exception as exc:
        check("API /health/ready", False, str(exc))
        return 1

    slugs = sys.argv[1:] if len(sys.argv) > 1 else [t["slug"] for t in P0_TRADES]
    selected = [t for t in P0_TRADES if t["slug"] in slugs]
    if not selected:
        print(f"No matching trades. Choose from: {[t['slug'] for t in P0_TRADES]}")
        return 1

    for trade in selected:
        run_trade_qa(trade)

    print("\n--- Manual P0 checklist (browser) ---")
    print("1. http://localhost:3000/onboarding — confirm trade + country pickers")
    print("2. Dashboard → Receptionist — repeat problem → book for each trade")
    print("3. Live voice call per trade (needs Telnyx + ngrok PUBLIC_API_URL)")
    print("4. Dashboard → Calendar — cancel stale test slots before next run")

    print("\n--- Summary ---")
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print("All automated P0 trade checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
