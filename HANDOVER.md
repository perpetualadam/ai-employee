# AI Employee — Agent Handover

Last updated: 2026-06-29  
Repo: https://github.com/perpetualadam/ai-employee.git  
Branch: `main` (latest: `bd160e1`)

This document is for the **next AI agent** continuing work on this project. Read it before making changes.

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
| 3 | AI text receptionist (Groq + tools) | Done |
| 4 | Voice calling (Telnyx TeXML + gather) | Done (needs reliability hardening) |
| 5 | Stripe billing + usage limits | Done |
| 6 | Onboarding wizard + checklist | Done |

**User is actively testing inbound voice calls** and has reported hearing loops, name/address intake skips, wrong booking times, and empty speech gathers. Many fixes were applied; **live re-test after the modular refactor is still needed**.

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

**Cursor rule:** `.cursor/rules/modular-architecture.mdc` (`alwaysApply: true`) — modular design, DRY, maintainable code. Do not duplicate logic; extend existing modules.

### Voice call flow

```
api/voice.py
  → voice/gather_handler.py      STT result → retry prompts or next turn
  → voice/call_service.py        Greeting, AI turn, TeXML orchestration
  → ai/receptionist_agent.py     LLM + tool loop
  → ai/receptionist_tools.py     CRM/calendar tool implementations
  → services/*                   Persistence
```

### Key modules

| Module | Responsibility |
|--------|----------------|
| `domain/intake.py` | Validate customer name and service address |
| `domain/phone.py` | Normalize phones, resolve caller ID |
| `domain/call.py` | Call-log helpers (e.g. booking detected) |
| `ai/conversation_state.py` | Shared session state for tools |
| `voice/session_state.py` | Phone-only intake guards and slot booking rules |
| `voice/slots.py` | Format slots, spoken times, slot matching |
| `voice/gather_prompts.py` | Empty/truncated speech retry messages |
| `voice/conversation.py` | Farewell / closing detection |
| `voice/texml_builder.py` | Telnyx XML responses |
| `voice/webhook_auth.py` | Telnyx Ed25519 webhook signature validation |
| `ai/receptionist_tools.py` | Tool implementations (delegates to VoiceSessionState in voice mode) |

### Deprecated re-exports (use domain/voice imports in new code)

- `voice/intake_utils.py` → `domain/intake.py`
- `voice/phone_utils.py` → `domain/phone.py`
- `voice/voice_intent.py` → `voice/conversation.py`, `voice/gather_prompts.py`, `domain/call.py`

---

## Recent git history

```
bd160e1  Add Cursor rule for modular, DRY, maintainable code.
c1beea1  Refactor voice stack into layered modules and harden phone booking.
c3c027e  Migrate voice to Telnyx and harden AI receptionist booking flow.
5d9f941  Initial commit: AI Employee MVP for trade businesses.
```

---

## Issues reported in testing & fixes applied

### 1. Voice "can't hear me" / loops / 500 errors

- **Root cause:** `AttributeError: 'TranscriptChunk' object has no attribute 'confidence'` in gather handling → every speech turn returned 500, Telnyx restarted call flow.
- **Fix:** Added `confidence: float | None = None` to `TranscriptChunk` in `voice/provider.py`; gather path passes confidence; callers use `getattr(chunk, "confidence", None)`.

### 2. Empty gathers / fragmented STT

- Many `Empty gather result` with `SpeechResult=""`, `Confidence=0.0` — caller speaking too early or during AI prompt.
- **Fixes:** beep before gather (`voice/static/beep.wav`), pause, longer timeout (30s), `speechTimeout="5"`, context-aware retry prompts in `voice/gather_prompts.py`.
- **User feedback:** "Go ahead" cue was confusing — **removed** from `texml_builder.py`.

### 3. AI skipping name/address intake & booking wrong customers

- `lookup_customer` found prior test records and allowed booking without fresh intake.
- **Fixes:** Voice mode requires `create_customer` success before availability/booking; placeholder name/address rejection; stricter address validation in `domain/intake.py` (must include street detail, not just state/city).

### 4. Wrong booking time (offered 11:30 AM, booked 11 AM)

- AI was inventing/rounding times instead of using exact slots.
- **Fixes:** `spoken_time` on each slot; `validate_and_resolve_slot()` in `VoiceSessionState`; prompts/tool descriptions require exact `start_time_utc`/`end_time_utc` from offered slots.

### 5. Telnyx webhook signature warnings (FIXED 2026-06-29)

- **Root cause:** Verifier signed the **query string** on TeXML GET callbacks; Telnyx signs `{timestamp}|{raw_body}` and GET gather has an **empty body**.
- **Fix:** `backend/app/voice/webhook_auth.py` — sign raw body only; support `v1a,` signature prefix and Standard Webhooks `webhook-id` fallback.
- `TELNYX_PUBLIC_KEY` is synced across `.env`, Docker, and container (not an env mismatch).
- In `DEBUG=true`, invalid signatures **warn but do not block**; in production (`DEBUG=false`) they return 403.
- Re-test on next live call — signature warnings should stop.

---

## Test context (from user's environment)

| Item | Value |
|------|--------|
| Business ID | `047694b9-6e63-4bbf-b186-280e0e23e968` |
| Test Telnyx number (US business line) | `+1 380 273 8396` |
| Dev test caller (owner's phone) | `+447492046947` |
| Voice mode | `VOICE_MODE=gather` (only supported mode for Telnyx) |

### Testing from outside the US (not a product requirement)

**Production:** Local US customers call a local US plumber number — short PSTN hop, `en-US` gather in `texml_builder.py`.

**Current dev setup:** Owner tests from a **UK mobile** to a **US Telnyx number**. You do **not** need US residency to **own** the business number (already on Telnyx). The UK line is only the **test caller**.

Calling UK → US can make voice tests **harder than production** (extra latency, call compression, UK accent vs `en-US` STT). Empty gathers or “please repeat” during dev may reflect **test conditions**, not a bug that US callers will hit.

**Recommended testing ladder:**

1. **Fastest — dashboard chat** (`/dashboard/receptionist`): same AI + booking tools, no phone. Use for intake, slots, and CRM logic daily.
2. **Voice smoke test — UK phone → US Telnyx number:** OK for webhooks, greeting, beep, gather, end-to-end sanity. Speak after the beep; quiet room.
3. **Pre-launch — one US PSTN test:** friend in the US, or Telnyx second US number + SIP softphone (Zoiper/Linphone) so both legs are US. Closest to real plumber traffic.

Do **not** treat “international caller tuning” as a backlog item unless US-local tests still fail.

### Local dev commands

```bash
# Backend + DB
docker compose up -d
docker compose restart api          # after code changes
docker compose logs -f api          # watch voice/gather logs

# Frontend
cd frontend && npm run dev          # http://localhost:3000

# Expose API for Telnyx webhooks
ngrok http 8000
# Set PUBLIC_API_URL=https://<ngrok-id>.ngrok-free.app in .env
```

API docs (debug): http://localhost:8000/docs

---

## Environment & secrets

- Copy `.env.example` → `.env` at repo root (docker-compose reads env vars from host).
- **Never commit:** `.env`, `ai employee local env.txt` (untracked; not in `.gitignore` yet — consider adding).
- Required for voice: `GROQ_API_KEY`, `TELNYX_API_KEY`, `TELNYX_PUBLIC_KEY`, `TELNYX_ACCOUNT_SID`, `TELNYX_PHONE_NUMBER`, `PUBLIC_API_URL`.
- Optional SMS: `TELNYX_MESSAGING_PROFILE_ID`.
- Billing: `STRIPE_*` vars (see README).

Telnyx TeXML app voice URL must point to:

- Inbound: `{PUBLIC_API_URL}/api/v1/voice/inbound`
- Gather callback is built into TeXML by `texml_builder.py`

In app **Settings**, business must set the same phone number and an escalation phone.

---

## What's left to do (prioritized)

### P0 — Voice reliability & verification

- [ ] Re-test on live call — Telnyx signature warnings should be gone after `webhook_auth.py` fix (2026-06-29).
- [ ] Optional live-call smoke test (Telnyx) — automated spec tests in `backend/tests/test_*_spec.py` cover intake, slots, and booking flow.
- [ ] Tune empty-gather handling if caller speaks too early (timing/beep UX — verify with US-local test before over-optimizing for UK→US dev calls).
- [ ] Confirm intake guards block stale test customer records in voice mode.

### P1 — Production deployment

- [ ] Deploy backend Docker container to VPS with HTTPS (replace ngrok).
- [ ] Deploy frontend to Vercel; set `NEXT_PUBLIC_API_URL`.
- [ ] Managed PostgreSQL or backed-up volume.
- [ ] Production secrets: strong `SECRET_KEY`, `DEBUG=false`, all integration keys.
- [ ] Point Telnyx TeXML app and Stripe webhook at production URLs.

### P2 — Product gaps

- [ ] **Call logs / transcript UI** — data exists in `call_logs.conversation_history`; dashboard only shows 10-row summary, no detail page or API route for full transcript.
- [ ] **Real email** — `NotificationService.send_email` only logs; no SMTP/SendGrid.
- [ ] **Per-tenant phone provisioning** — inbound routing works via `business.phone_number`, but numbers are manually assigned in Telnyx + Settings (no automation).
- [ ] Update **README** — still says "AI & Voice (prepared, not yet wired)"; outdated.

### P3 — Quality & maintainability

- [ ] **Automated spec tests** — `backend/tests/test_intake_spec.py`, `test_voice_slots_spec.py`, `test_voice_session_spec.py`, `test_voice_receptionist_spec.py`, `test_webhook_auth.py`. Run: `docker compose exec api python -m unittest discover -s tests -v`
- [ ] Add `ai employee local env.txt` (or `*local env*`) to `.gitignore`.
- [ ] Remove deprecated re-export shims once imports are migrated.
- [ ] CI/CD (GitHub Actions) — not present.

### P4 — Optional upgrades (post-MVP)

- [ ] Real-time voice streaming (`VOICE_MODE=stream` + Deepgram) — **not implemented** for Telnyx; `media_stream_handler.py` rejects WebSocket connections.
- [ ] Appointment reminders (SMS/email cron).
- [ ] Outbound calls (schema supports; not built).
- [ ] Monitoring (Sentry, uptime, call failure alerts).

---

## Frontend pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Overview, stats, recent calls/customers/AI activity |
| `/dashboard/receptionist` | Text chat test of AI receptionist |
| `/dashboard/customers` | CRM |
| `/dashboard/jobs` | Jobs |
| `/dashboard/calendar` | Appointments |
| `/dashboard/settings` | Business profile, phone, hours, AI instructions |
| `/dashboard/billing` | Stripe checkout/portal, usage |
| `/onboarding` | Setup wizard |

**Missing:** dedicated Calls page with transcript drill-down.

---

## API endpoints (high level)

See README for full list. Voice-specific:

| Method | Path | Description |
|--------|------|-------------|
| POST/GET | `/api/v1/voice/inbound` | Telnyx inbound call webhook |
| POST/GET | `/api/v1/voice/gather` | Speech gather callback |
| POST | `/api/v1/voice/status` | Call status callback |
| WS | `/api/v1/voice/stream` | Legacy — rejects; use gather mode |

AI chat: `POST /api/v1/receptionist/chat`

---

## Billing & limits

- 14-day free trial on Starter limits (`backend/app/billing/plans.py`).
- Starter: 100 calls/mo, 500 AI tool calls/mo ($49).
- Pro: 500 calls/mo, 5000 AI tool calls/mo ($99).
- Voice and AI blocked when trial expired or over limit (`core/deps.py`, `subscription_service.py`).

---

## Multi-tenancy

- Every tenant table has `business_id`.
- API resolves authenticated user's business and scopes all queries.
- Inbound voice: `find_business_by_phone()` in `call_service.py` matches `Business.phone_number` to called Telnyx number.
- Single Telnyx account in env today; per-business numbers configured manually.

---

## Notifications

| Channel | Status |
|---------|--------|
| SMS | Telnyx when configured; dev mode logs only |
| Email | Dev log only — no real provider |

Booking confirmation SMS is triggered from `receptionist_tools.py` via `NotificationService`.

---

## Suggested next-agent workflow

1. Read `backend/app/ARCHITECTURE.md` and `.cursor/rules/modular-architecture.mdc`.
2. Check `docker compose logs -f api` during a test call.
3. If voice issues: trace `gather_handler.py` → `call_service.py` → `receptionist_agent.py` → `receptionist_tools.py` → `session_state.py`.
4. Do not put business logic in `api/` routes or duplicate validation outside `domain/`.
5. Only commit when user explicitly asks. Never commit `.env` or `ai employee local env.txt`.

---

## Prior conversation reference

Extended debugging and refactor context lives in agent transcript:

`C:\Users\Brian\.cursor\projects\c-Users-Brian-OneDrive-Desktop-AI-Employee-for-Traders\agent-transcripts\0acc2ceb-46cd-423a-9ddd-ed6d17fa383b\0acc2ceb-46cd-423a-9ddd-ed6d17fa383b.jsonl`

Search keywords: `TranscriptChunk`, `Empty gather`, `validate_and_resolve_slot`, `VoiceSessionState`, `TELNYX_PUBLIC_KEY`.

---

## User preferences (from rules)

- Modular, DRY code — smallest correct diff, no drive-by refactors.
- Do not commit unless explicitly requested.
- Do not create markdown files unless asked (this handover was explicitly requested).
- Use existing conventions; match surrounding code style.
