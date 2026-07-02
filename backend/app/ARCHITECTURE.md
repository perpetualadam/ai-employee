# Backend module layout

This document describes how the backend is organized for maintenance and extension.

Last updated: 2026-06-30 (aligned with root `HANDOVER.md`).

---

## Implementation status

What is **built and on `main`** vs what remains.

### Built (receptionist core)

| Capability | Status | Key files |
|------------|--------|-----------|
| Groq LLM + tool loop | Done | `ai/receptionist_agent.py`, `ai/provider.py` |
| CRM tools (lookup, create customer) | Done | `ai/receptionist_tools.py`, `services/customer_service.py` |
| Calendar availability + booking | Done | `services/appointment_service.py` |
| Next-day fallback when date full | Done | `find_next_available()` |
| Unified session guards (voice + text) | Done | `voice/session_state.py`, `receptionist_tools.py` |
| Exact slot booking | Done | `voice/slots.py`, `validate_and_resolve_slot()` |
| Intake validation (name, address) | Done | `domain/intake.py` |
| Telnyx voice (TeXML gather) | Done | `voice/call_service.py`, `texml_builder.py` |
| Telnyx webhook auth | Done | `voice/webhook_auth.py` |
| SMS + owner escalation notify | Done* | `services/notification_service.py` (*needs Telnyx messaging config in prod) |
| Escalation: block scheduling-only | Done | `receptionist_tools.transfer_call()` |
| Spec tests (32) | Done | `backend/tests/test_*_spec.py` |

### Not built / out of scope for current MVP

| Capability | Status |
|------------|--------|
| Real-time voice streaming (`VOICE_MODE=stream`) | Not implemented — WebSocket rejected |
| Call transcript HTTP API + UI | Data in DB; no dedicated route |
| Real email delivery | Logs only |
| Automated phone number provisioning | Manual Telnyx + Settings |
| CI pipeline | `.github/workflows/ci.yml` on push/PR to `main` |
| Outbound calling | Schema only |

### Needs live verification (code complete, QA pending)

- Text chat booking flow after `21141b2` guards
- Voice call end-to-end on real Telnyx number
- Owner/customer SMS with production Telnyx messaging profile

---

## Layer overview

```
app/
├── api/              HTTP routes (thin — validate input, call services, return response)
├── ai/               AI agent, tools, prompts, conversation state
├── domain/           Business rules with no HTTP or Telnyx dependencies
├── services/         CRM, calendar, billing, auth (database + tenant scope)
├── models/           SQLAlchemy models
├── schemas/          Pydantic request/response types
├── voice/            Telnyx TeXML, STT/TTS adapters, voice-only flow
├── billing/          Stripe plan definitions
└── core/             Auth deps, logging, security
```

**Dependency rule:** outer layers may import inner layers, not the reverse.

- `api` → `services`, `voice`, `ai`
- `voice` → `ai`, `domain`, `services`
- `ai` → `domain`, `services`
- `domain` → (stdlib only)
- `services` → `models`, `domain` (optional)

---

## Voice call flow

```
api/voice.py
  → voice/gather_handler.py     (STT result → retry prompts or next turn)
  → voice/call_service.py         (orchestration: greeting, AI turn, TeXML)
  → ai/receptionist_agent.py      (LLM + tool loop)
  → ai/receptionist_tools.py      (CRM/calendar tool implementations)
  → services/*                    (persistence)
```

---

## Text chat flow (dashboard receptionist preview)

Same agent and tools as voice; differs only in `voice_mode=False` on `ReceptionistAgent.chat()`.

```
api/receptionist.py
  → ai/receptionist_agent.py      (LLM + tool loop; sets user_turn_count)
  → ai/receptionist_tools.py      (same tool impl; VoiceSessionState guards)
  → services/*                    (persistence)
```

Each chat session gets a `call_log_id` (stored on the frontend). Tool state is restored from `AIActivityLog` rows for that session, same as phone calls.

---

## Session state & booking guards

**Important:** Both voice and text use `VoiceSessionState` (via `VoiceSessionState.load()` in `receptionist_tools.py`). The base `ConversationState` class holds shared fields and is extended by `VoiceSessionState` for intake/slot/SMS guards.

| Guard | Where | Voice | Text |
|-------|-------|-------|------|
| Intake before availability/booking | `VoiceSessionState.require_intake()` | Yes | Yes |
| No booking same turn as first availability | `VoiceSessionState.block_same_turn_booking()` | Yes | Yes |
| Exact slot match only | `VoiceSessionState.validate_and_resolve_slot()` | Yes | Yes |
| No `create_customer` on turn 1 | `receptionist_tools.create_customer()` + `user_turn_count` | No | Yes (`user_turn_count < 2`) |
| One confirmation SMS per session | `VoiceSessionState.sms_sent_this_call` | Yes | Yes |
| No escalate for full calendar | `receptionist_tools.transfer_call()` | Yes | Yes |

`user_turn_count` is set in `receptionist_agent.py` from chat history length (+ current message). Voice calls leave it at 0 so intake is governed only by session guards and prompts.

State is rebuilt from prior tool logs in `VoiceSessionState.apply_voice_activity_log()` — including offered slots from `check_availability` (`slots` or `next_slots`) and `sms_sent_this_call` from successful `send_sms`.

**When changing any row in this table:** update `ai/prompts.py`, the guard in code, and extend `backend/tests/test_*_spec.py`.

---

## Key modules

| Module | Responsibility |
|--------|----------------|
| `domain/intake.py` | Validate customer name and service address |
| `domain/phone.py` | Normalize phone numbers, resolve caller ID |
| `domain/call.py` | Call-log helpers (e.g. booking detected) |
| `ai/conversation_state.py` | Base session fields; loads from `AIActivityLog` |
| `voice/session_state.py` | **Unified** intake guards, slot booking rules, SMS dedup (voice + text) |
| `voice/slots.py` | Format slots, spoken times, slot matching |
| `voice/gather_prompts.py` | Empty/truncated speech retry messages |
| `voice/conversation.py` | Farewell / closing detection |
| `voice/texml_builder.py` | Telnyx XML responses |
| `voice/webhook_auth.py` | Telnyx Ed25519 webhook signature validation |
| `voice/provider.py` | Swappable voice/STT/TTS interfaces |
| `ai/receptionist_agent.py` | LLM loop, tool dispatch, escalation side-effects |
| `ai/receptionist_tools.py` | Tool implementations; delegates guards to `VoiceSessionState` |
| `ai/prompts.py` | System prompts (separate voice vs text workflow sections) |
| `ai/provider.py` | Swappable AI provider interface (Groq) |
| `services/appointment_service.py` | Calendar CRUD, `get_availability`, `find_next_available` |
| `services/notification_service.py` | SMS (Telnyx), owner escalation alerts |

---

## Escalation behavior

`transfer_call` in `receptionist_tools.py`:

- **Blocked** when reason is scheduling-only ("no slots", "fully booked", etc.) — agent must offer `next_slots` instead.
- **Voice:** live Telnyx transfer to `business.escalation_phone` when `external_call_id` exists.
- **Text chat:** no live transfer; `NotificationService.notify_owner_escalation()` SMS to owner. Response includes `owner_notified` on `ChatResponse`.

---

## Spec tests

Run inside the API container (or locally with `PYTHONPATH=.` from `backend/`):

```bash
docker compose exec api python -m unittest discover -s tests -v
```

| File | Covers |
|------|--------|
| `test_intake_spec.py` | Name/address validation |
| `test_voice_session_spec.py` | Session guards (voice + text via `VoiceSessionState`) |
| `test_voice_slots_spec.py` | Slot formatting, exact-time booking |
| `test_voice_receptionist_spec.py` | End-to-end voice tool flow across turns |
| `test_text_receptionist_spec.py` | Text chat: `user_turn_count`, same-turn book, SMS dedup |
| `test_webhook_auth.py` | Telnyx webhook signatures |
| `test_*_spec.py` (others) | Conversations, gather prompts, public chat, etc. |

CI (`.github/workflows/ci.yml`) runs the full suite on every push/PR to `main`.

---

## Adding features

- **New business rule** (name validation, address rules) → `domain/`
- **New CRM/calendar behavior** → `services/` + wire in `ai/receptionist_tools.py`
- **New voice UX** (prompts, STT handling) → `voice/` only
- **New text-chat UX** → `ai/prompts.py` + guards in `receptionist_tools.py` / `session_state.py`
- **New HTTP endpoint** → `api/` + existing service
- **New external provider** → implement `ai/provider.py` or `voice/provider.py` ABC

When changing booking behavior, update **prompts + session guards + spec tests** together.

---

## Remaining backend work (from handover)

| Priority | Task |
|----------|------|
| P0 | User QA on text + voice booking paths |
| P1 | Production deploy, HTTPS, prod env |
| P2 | `GET /calls/{id}` or similar for full transcript; real email |
| P3 | ~~Text spec tests, CI, delete shims~~ | **Done** (2026-06-30) |
| P4 | Stream mode, reminders, outbound, monitoring |

See root `HANDOVER.md` for full product-wide backlog.
