# Backend module layout

This document describes how the backend is organized for maintenance and extension.

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

## Voice call flow

```
api/voice.py
  → voice/gather_handler.py     (STT result → retry prompts or next turn)
  → voice/call_service.py         (orchestration: greeting, AI turn, TeXML)
  → ai/receptionist_agent.py      (LLM + tool loop)
  → ai/receptionist_tools.py      (CRM/calendar tool implementations)
  → services/*                    (persistence)
```

## Key modules

| Module | Responsibility |
|--------|----------------|
| `domain/intake.py` | Validate customer name and service address |
| `domain/phone.py` | Normalize phone numbers, resolve caller ID |
| `domain/call.py` | Call-log helpers (e.g. booking detected) |
| `ai/conversation_state.py` | Shared session state for tools (voice + text) |
| `voice/session_state.py` | Phone-only intake guards and slot booking rules |
| `voice/slots.py` | Format slots, spoken times, slot matching |
| `voice/gather_prompts.py` | Empty/truncated speech retry messages |
| `voice/conversation.py` | Farewell / closing detection |
| `voice/texml_builder.py` | Telnyx XML responses |
| `voice/provider.py` | Swappable voice/STT/TTS interfaces |
| `ai/provider.py` | Swappable AI provider interface |

## Adding features

- **New business rule** (name validation, address rules) → `domain/`
- **New CRM/calendar behavior** → `services/` + wire in `ai/receptionist_tools.py`
- **New voice UX** (prompts, STT handling) → `voice/` only
- **New HTTP endpoint** → `api/` + existing service
- **New external provider** → implement `ai/provider.py` or `voice/provider.py` ABC

## Deprecated re-exports

These files remain for backward compatibility; import from `domain/` in new code:

- `voice/intake_utils.py` → `domain/intake.py`
- `voice/phone_utils.py` → `domain/phone.py`
- `voice/voice_intent.py` → `voice/conversation.py`, `voice/gather_prompts.py`, `domain/call.py`
