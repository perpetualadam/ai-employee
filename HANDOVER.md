# AI Employee — Agent Handover

Last updated: 2026-06-30  
Repo: https://github.com/perpetualadam/ai-employee.git  
Branch: `main` (latest: `21141b2`)

This document is for the **next AI agent** continuing work on this project. Read it before making changes.

---

## Progress at a glance

Summary of the **original handover backlog** (2026-06-29) vs current state.

### Completed — code shipped to `main`

| Area | Item | Commit / evidence |
|------|------|-------------------|
| Voice | Telnyx migration (Twilio removed) | `c3c027e` |
| Voice | Modular voice stack (`gather_handler`, `call_service`, `domain/`) | `c1beea1` |
| Voice | `TranscriptChunk.confidence` — fixed 500 loops on gather | `c1beea1` |
| Voice | Empty-gather UX: beep, longer timeout, retry prompts | `c1beea1` |
| Voice | Intake guards — `create_customer` required before book | `c1beea1` |
| Voice | Exact slot booking (`validate_and_resolve_slot`, `spoken_time`) | `c1beea1` |
| Voice | Stale CRM records cannot bypass intake | tests: `test_stale_test_record_*`, `test_lookup_alone_*` |
| Voice | Telnyx webhook signature (GET gather empty body) | `8d23252`, `test_webhook_auth.py` |
| Calendar | Full day → offer next open day, not escalate | `e4fd749`, `find_next_available()` |
| Escalation | Block `transfer_call` for scheduling-only reasons | `e4fd749` |
| Escalation | Owner SMS on **text chat** escalation | `8d23252`, `owner_notified` on `ChatResponse` |
| Text chat | Unified `VoiceSessionState` guards (intake, slots, SMS dedup) | `21141b2` |
| Text chat | No `create_customer` on turn 1 (`user_turn_count`) | `21141b2` |
| Text chat | Prompts: one question at a time, no re-greet, no dup confirm | `21141b2` |
| Frontend | Receptionist: "Behind the scenes" tool log, `owner_notified` | `8d23252` / `21141b2` |
| Frontend | Removed dev "Start a new session" escalation banner | `8d23252` |
| Frontend | React duplicate key fix on tool badges | `8d23252` |
| Quality | 32 automated spec tests (intake, slots, session, flow, webhooks) | `backend/tests/` |
| Quality | Cursor modular-architecture rule | `bd160e1` |
| Docs | This handover + `backend/app/ARCHITECTURE.md` | ongoing |

### Partially done — code in place, may need tuning or config

| Item | Status |
|------|--------|
| Empty-gather / STT timing | Beep + retries shipped; **live US-local test** may still need timing tweaks |
| Customer confirmation SMS | Works when `TELNYX_MESSAGING_PROFILE_ID` set; otherwise dev-log only |
| Owner escalation SMS | Code path exists; **Telnyx 400** reported in dev — messaging profile / number config |
| Deprecated re-export shims | Files still exist; **no imports remain** in `backend/app/` — safe to delete |

### Awaiting user verification (not confirmed in testing yet)

| Item | How to verify |
|------|----------------|
| Text chat full booking flow | New session → "no hot water" → name → address → slots → book → "no bye" (see script below) |
| Voice live call end-to-end | Call US Telnyx number after beep; check logs for signature warnings + booking |
| Telnyx signature warnings gone | `docker compose logs -f api` during live call — no repeated verify failures |
| Calendar not blocking tests | Cancel stale appointments on **Dashboard → Calendar** before slot tests |

### Not started — still on the backlog

| Priority | Item |
|----------|------|
| **P1** | Production deploy (VPS, HTTPS, Vercel frontend, managed Postgres, prod secrets) |
| **P2** | Call logs / full transcript UI + API |
| **P2** | Real email (SMTP/SendGrid) |
| **P2** | Automated per-tenant phone provisioning |
| **P2** | Update README ("AI & Voice prepared, not yet wired" is outdated) |
| **P3** | Text-chat-specific spec tests (`user_turn_count` path) |
| **P3** | Add `*local env*` to `.gitignore` (`.env` already ignored) |
| **P3** | Delete deprecated voice re-export shims |
| **P3** | CI/CD (GitHub Actions) |
| **P4** | Real-time voice streaming, reminders cron, outbound calls, monitoring |

---

## What this product is

**AI Employee** is a multi-tenant SaaS AI phone receptionist for trade businesses (plumbers, HVAC, etc.).

Core capabilities:

- Answers inbound phone calls (Telnyx TeXML + speech gather)
- Qualifies leads via LLM conversation (Groq)
- Books appointments on an internal calendar
- Manages a simple CRM (customers, jobs)
- Sends SMS confirmations (Telnyx, when configured)
- Stripe billing with trial and usage limits
- Next.js dashboard for business owners

---

## Current state: MVP built, production not shipped

README marks Phases 1–6 as **Done**. The codebase is a **functional MVP**, not yet **production-ready SaaS**.

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | Database, auth, dashboard shell | Done |
| 2 | CRM + appointments API & UI | Done |
| 3 | AI text receptionist (Groq + tools) | Done — hardened 2026-06-30 |
| 4 | Voice calling (Telnyx TeXML + gather) | Done — **needs live re-test** |
| 5 | Stripe billing + usage limits | Done |
| 6 | Onboarding wizard + checklist | Done |

**Bottom line for next agent:** Most **reported bugs are fixed in code**. The main gap is **user QA on text + voice** and **production deployment / product polish** (transcripts UI, email, CI).

---

## Architecture (must follow)

Full layout: `backend/app/ARCHITECTURE.md`

```
app/
├── api/           HTTP routes (thin — validate, delegate, respond)
├── ai/            Agent, tools, prompts, conversation_state
├── domain/        Business rules — NO HTTP, Telnyx, DB, or LLM imports
├── services/      CRM, calendar, billing, auth (DB + tenant scope)
├── voice/         Telnyx, STT, TeXML, voice-only flow
├── models/        SQLAlchemy
├── schemas/       Pydantic DTOs
└── core/          Auth, logging, security
```

**Dependency rule:** outer layers import inner only (`api` → `services`/`voice`/`ai` → `domain`).

**Cursor rule:** `.cursor/rules/modular-architecture.mdc` (`alwaysApply: true`).

### Voice call flow

```
api/voice.py → gather_handler → call_service → receptionist_agent → receptionist_tools → services/*
```

### Text chat flow

```
api/receptionist.py → receptionist_agent (voice_mode=False) → receptionist_tools → services/*
```

### Key modules

| Module | Responsibility |
|--------|----------------|
| `voice/session_state.py` | **Unified** intake guards, slot rules, SMS dedup (voice + text) |
| `ai/receptionist_tools.py` | Tool implementations; always uses `VoiceSessionState` |
| `services/appointment_service.py` | Calendar + `find_next_available()` |
| `services/notification_service.py` | SMS + `notify_owner_escalation()` |
| `voice/webhook_auth.py` | Telnyx Ed25519 signature validation |

See `backend/app/ARCHITECTURE.md` for the full module table.

---

## Recent git history

```
21141b2  Harden text chat booking to match voice intake and slot guards.
e4fd749  Offer next-day slots when calendar is full instead of escalating.
8d23252  Notify owners on chat escalation and fix Telnyx webhook verification.
bd160e1  Add Cursor rule for modular, DRY, maintainable code.
c1beea1  Refactor voice stack into layered modules and harden phone booking.
c3c027e  Migrate voice to Telnyx and harden AI receptionist booking flow.
5d9f941  Initial commit: AI Employee MVP for trade businesses.
```

---

## Booking flow contract (voice + text)

1. Greet → problem → name → address → phone (caller ID or ask)
2. `create_customer` must succeed before availability or booking
3. `check_availability` → offer slots → **wait** (no book same turn)
4. Next message: customer picks slot → `book_appointment` once (exact UTC times)
5. One confirmation SMS → brief goodbye on "no" / "bye"

Text-only: `create_customer` blocked until `user_turn_count >= 2`.  
Full calendar: offer `next_slots` — never escalate for scheduling alone.

---

## Issues reported & fix status

| # | Issue | Fix status | User verified? |
|---|-------|------------|----------------|
| 1 | Voice 500 / loops (`TranscriptChunk`) | Fixed | Unknown |
| 2 | Empty gathers / STT timing | Mitigated (beep, retries) | Unknown |
| 3 | Skipped name/address intake | Fixed | Covered by spec tests |
| 4 | Wrong booking time (rounded slots) | Fixed | Covered by spec tests |
| 5 | Telnyx webhook signature warnings | Fixed | **Pending live call** |
| 6 | Text chat skipped intake / dup SMS | Fixed (`21141b2`) | **Pending retest** |
| 7 | Escalation when calendar full | Fixed (`e4fd749`) | Pending retest |
| 8 | Chat escalation no owner notify | Fixed (`8d23252`) | SMS may still 400 |

---

## Known open issues

| Issue | Notes |
|-------|--------|
| Owner escalation SMS 400 | Telnyx messaging config — `owner_notified: false` until fixed |
| Test calendar clutter | Cancel appointments on **Dashboard → Calendar** |
| README outdated | Still says voice "not yet wired" |
| `ai employee local env.txt` | Untracked secrets file; not in `.gitignore` |
| HANDOVER / ARCHITECTURE docs | Updated locally; **not yet committed** to GitHub |

---

## Test context

| Item | Value |
|------|--------|
| Business ID | `047694b9-6e63-4bbf-b186-280e0e23e968` |
| Test Telnyx number | `+1 380 273 8396` |
| Dev test caller | `+447492046947` |
| Voice mode | `VOICE_MODE=gather` |

### Text chat retest script

New session. Optional Caller ID: `+447492046947`.

| Step | User says | Expected |
|------|-----------|----------|
| 1 | "I have no hot water" | Ask for **name** |
| 2 | Full name | Ask for **address** |
| 3 | Full street address | Offer real slots |
| 4 | "8am" | **One** booking confirmation |
| 5 | "no bye" | Brief goodbye only |

### Local dev commands

```bash
docker compose up -d
docker compose up -d --force-recreate api   # after backend changes
docker compose exec api python -m unittest discover -s tests -v   # 32 tests
cd frontend && npm run dev
ngrok http 8000   # set PUBLIC_API_URL in .env
```

---

## What's left to do (prioritized checklist)

Use `[x]` / `[ ]` when updating this list.

### P0 — Verify fixes (user / QA)

- [ ] Re-test text chat: intake → slots → book → goodbye
- [ ] Re-test voice live call (signature + intake + booking)
- [ ] Fix owner escalation SMS if `owner_notified: false`
- [ ] Clear stale test appointments before slot tests

### P1 — Production deployment

- [ ] Backend on VPS with HTTPS (replace ngrok)
- [ ] Frontend on Vercel; `NEXT_PUBLIC_API_URL`
- [ ] Managed PostgreSQL or backed-up volume
- [ ] Prod secrets: `SECRET_KEY`, `DEBUG=false`, integration keys
- [ ] Telnyx TeXML + Stripe webhooks → production URLs

### P2 — Product gaps

- [ ] Call logs / transcript UI (`call_logs.conversation_history` exists; no drill-down UI)
- [ ] Real email provider
- [ ] Per-tenant phone auto-provisioning
- [ ] Update README

### P3 — Quality & maintainability

- [x] Automated spec tests (32)
- [ ] Text-chat-specific spec tests
- [ ] `.gitignore` for `*local env*`
- [ ] Remove deprecated voice re-export shims (no app imports left)
- [ ] CI/CD (GitHub Actions)

### P4 — Post-MVP optional

- [ ] Real-time voice streaming (`VOICE_MODE=stream` — not implemented)
- [ ] Appointment reminders
- [ ] Outbound calls
- [ ] Monitoring (Sentry, uptime)

---

## Frontend pages

| Route | Purpose |
|-------|---------|
| `/dashboard/receptionist` | Text chat test (Caller ID, "Behind the scenes") |
| `/dashboard/calendar` | Appointments — cancel test bookings here |
| `/dashboard/settings` | Phone, escalation phone, AI instructions |
| `/dashboard` | Overview |

**Missing:** `/dashboard/calls` with transcript drill-down.

---

## API endpoints (high level)

| Method | Path | Description |
|--------|------|-------------|
| POST/GET | `/api/v1/voice/inbound` | Telnyx inbound |
| POST/GET | `/api/v1/voice/gather` | Speech gather |
| POST | `/api/v1/receptionist/chat` | Text chat (`owner_notified` on escalate) |

---

## Suggested next-agent workflow

1. Read `backend/app/ARCHITECTURE.md`.
2. Run spec tests (expect 32 passing).
3. If booking bugs: `receptionist_tools.py` → `session_state.py` → `prompts.py`.
4. If voice bugs: `gather_handler.py` → `call_service.py` → same tools path.
5. Update **prompts + guards + tests** together when changing booking behavior.
6. Only commit when user asks. Never commit `.env` or `ai employee local env.txt`.

---

## Prior conversation reference

`C:\Users\Brian\.cursor\projects\c-Users-Brian-OneDrive-Desktop-AI-Employee-for-Traders\agent-transcripts\0acc2ceb-46cd-423a-9ddd-ed6d17fa383b\0acc2ceb-46cd-423a-9ddd-ed6d17fa383b.jsonl`

Search: `no hot water`, `user_turn_count`, `find_next_available`, `owner_notified`.

---

## User preferences

- Smallest correct diff; no drive-by refactors.
- Do not commit unless explicitly requested.
- Match existing code conventions.
