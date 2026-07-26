# AI Employee — Agent Handover

Last updated: 2026-07-03  
Repo: https://github.com/perpetualadam/ai-employee.git  
Branch: `main` (latest: see `git log -1`)

This document is for the **next AI agent** continuing work on this project. Read it before making changes.

---

## Progress at a glance

The MVP and planned feature tiers **P1–P4 are implemented in code**. What remains is mostly **user QA** and **production deploy** (accounts, DNS, secrets).

### Recently shipped (2026-07)

| Area | Item |
|------|------|
| Calendar | Bulk select + bulk cancel appointments |
| Trades | 14-industry template registry + country compliance |
| Deploy | Full-stack VPS Docker (`docker-compose.prod.yml`, Caddy, scripts) |
| QA | `P0_QA.md` + `scripts/p0_trade_qa.py` for multi-trade smoke |
| Voice | Deepgram stream mode (`VOICE_MODE=stream`) when `DEEPGRAM_API_KEY` + Telnyx configured |
| Monitoring | Sentry backend (`SENTRY_DSN`) + frontend (`NEXT_PUBLIC_SENTRY_DSN`) |
| Marketing | Fair-launch landing page polish |

### Test suite

```bash
docker compose exec api python -m unittest discover -s tests -v
```

**Expect 116+ passing tests** (voice, text, trades, appointments, webhooks, P4, etc.).

CI: `.github/workflows/ci.yml` — backend tests + frontend lint/build on `main`.

---

## What this product is

**AI Employee** is a multi-tenant SaaS AI phone receptionist for trade businesses.

Core capabilities:

- Answers inbound phone calls (Telnyx TeXML gather, optional Deepgram stream STT)
- Qualifies leads via LLM conversation (Groq)
- Books appointments on an internal calendar (bulk cancel for QA cleanup)
- Manages CRM (customers, jobs) + conversation inbox
- Sends SMS/email confirmations (Telnyx + SMTP when configured)
- Stripe billing with trial and usage limits
- Multi-trade onboarding (14 industries, country compliance)
- Next.js dashboard for business owners

---

## Current state

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | Database, auth, dashboard shell | Done |
| 2 | CRM + appointments API & UI | Done |
| 3 | AI text receptionist (Groq + tools) | Done |
| 4 | Voice calling (Telnyx TeXML + gather / Deepgram stream) | Done — **needs live re-test** |
| 5 | Stripe billing + usage limits | Done |
| 6 | Onboarding wizard + multi-trade templates | Done |
| P1 | Production packaging | Done in repo — **user deploy manual** |
| P2–P4 | Inbox, email, provisioning, reminders, outbound, monitoring | Done |

**Bottom line:** Code is launch-ready. Gaps are **P0 manual QA**, **production secrets/DNS**, and **live voice verification**.

---

## Voice modes

| `VOICE_MODE` | Behavior |
|--------------|----------|
| `gather` (default) | Telnyx TeXML `<Gather input="speech">` — recommended for production |
| `stream` | TeXML `<Stream>` → WebSocket → Deepgram live STT → `update_call_texml` for next turn |

Stream requires: `DEEPGRAM_API_KEY`, `TELNYX_ACCOUNT_SID`, `TELNYX_TEXML_CONNECTION_ID`, `PUBLIC_API_URL` (HTTPS/WSS in prod).

Check: `GET /api/v1/voice/mode` or `/health` → `voice_mode`.

---

## Monitoring (Sentry)

| Env var | Where |
|---------|--------|
| `SENTRY_DSN` | Backend API — auto-init in `app/core/monitoring.py` |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend — `SentryInit` in landing layout |

Both optional; skipped when unset. `/health` reports `"monitoring": {"sentry": true|false}`.

---

## Architecture (must follow)

Full layout: `backend/app/ARCHITECTURE.md`

```
app/
├── api/           HTTP routes (thin)
├── ai/            Agent, tools, prompts
├── domain/        Business rules — NO HTTP, Telnyx, DB, or LLM imports
├── domain/trades/ Multi-trade templates + compliance
├── services/      CRM, calendar, billing, voice_mode
├── voice/         Telnyx, STT, TeXML, stream handler
└── core/          Auth, logging, monitoring (Sentry)
```

**Cursor rule:** `.cursor/rules/modular-architecture.mdc`

### Voice call flow

```
api/voice.py → gather_handler OR voice_stream_service → call_service → receptionist_agent → tools
```

---

## Recent git history (high level)

```
54f0255  Ignore accidental nested ai-employee clone directory.
32f984e  Add bulk cancel for calendar appointments.
7dd06be  Fix gather_handler indent + P0 multi-trade QA script.
0919af9  Multi-trade template registry.
3216979  Full-stack VPS deployment.
abc1942  P1 production deployment packaging.
```

---

## Booking flow contract (voice + text)

1. Greet → problem → name → address → phone (caller ID or ask)
2. `create_customer` must succeed before availability or booking
3. `check_availability` → offer slots → **wait** (no book same turn)
4. Next message: customer picks slot → `book_appointment` once
5. One confirmation SMS → brief goodbye on "no" / "bye"

Text-only: `create_customer` blocked until `user_turn_count >= 2`.

---

## What's left (prioritized)

### P0 — User QA (see `P0_QA.md`)

- [ ] Text booking for 3 trades (plumbing US, gas engineer GB, mobile mechanic US)
- [ ] Live voice call (Telnyx + ngrok or production URL)
- [ ] Calendar cleanup via bulk cancel after tests

### P1 — Production deploy (see `DEPLOY.md`)

- [ ] VPS + DNS + `.env` secrets
- [ ] Telnyx + Stripe webhooks → HTTPS API
- [ ] Optional: `SENTRY_DSN`, `DEEPGRAM_API_KEY`, `VOICE_MODE=stream`

---

## Local dev commands

```bash
docker compose up -d
# Migrations run automatically via docker-entrypoint.sh on API start
docker compose exec api python -m unittest discover -s tests -v
docker compose exec api python scripts/p0_trade_qa.py
cd frontend && npm install && npm run dev
ngrok http 8000   # set PUBLIC_API_URL in .env for voice webhooks
```

---

## Frontend pages

| Route | Purpose |
|-------|---------|
| `/` | Fair-launch marketing landing |
| `/dashboard/receptionist` | Text chat test |
| `/dashboard/calendar` | Appointments — bulk cancel for QA |
| `/dashboard/conversations` | Inbox + transcripts |
| `/dashboard/settings` | Phone, escalation, AI instructions |

---

## Suggested next-agent workflow

1. Read `backend/app/ARCHITECTURE.md`.
2. Run spec tests (expect **116+** passing).
3. Booking bugs: `receptionist_tools.py` → `session_state.py` → `prompts.py`.
4. Voice bugs: `gather_handler.py` / `voice_stream_service.py` → `call_service.py`.
5. Only commit when user asks. Never commit `.env` or local env files.

---

## User preferences

- Smallest correct diff; no drive-by refactors.
- Do not commit unless explicitly requested.
- Match existing code conventions.
