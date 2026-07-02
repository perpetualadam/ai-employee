# AI Employee

AI receptionist SaaS for trade businesses. Answers calls and chats, qualifies leads, books jobs, sends confirmations, and updates a simple CRM.

## Architecture

```
┌─────────────────┐     REST/JWT      ┌──────────────────┐
│  Next.js 15     │ ◄──────────────► │  FastAPI         │
│  (Vercel)       │                   │  (VPS/Docker)    │
└─────────────────┘                   └────────┬─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼───────┐          ┌───────▼───────┐
              │ PostgreSQL │            │  Groq API     │          │ Telnyx        │
              │ (multi-    │            │  (LLM)        │          │ Voice + SMS   │
              │  tenant)   │            └───────────────┘          └───────────────┘
              └───────────┘
```

### Multi-tenancy

Every tenant-scoped table includes `business_id`. API routes resolve the authenticated user's business and filter all queries by that ID.

### Database schema

| Table | Purpose |
|-------|---------|
| `users` | Business owner accounts |
| `businesses` | Tenant root — profile, hours, AI instructions |
| `business_services` | Services offered (drain cleaning, etc.) |
| `business_emergency_rules` | Urgency detection rules |
| `customers` | CRM contacts (unique phone per business) |
| `jobs` | Work orders linked to customers |
| `appointments` | Internal calendar |
| `call_logs` | Calls, chats, SMS — includes `conversation_history` JSON |
| `ai_activity_logs` | AI tool call audit trail |

### AI, voice, and inbox (wired)

| Layer | Key modules |
|-------|-------------|
| AI receptionist | `backend/app/ai/receptionist_agent.py`, `receptionist_tools.py`, `prompts.py` |
| Voice (Telnyx TeXML) | `backend/app/voice/call_service.py`, `gather_handler.py`, `api/voice.py` |
| Unified inbox | `backend/app/services/conversation_service.py`, `api/conversations.py` |
| Notifications | `backend/app/services/notification_service.py` — Telnyx SMS + SMTP email |

Dashboard **Inbox** (`/dashboard/conversations`) shows every conversation with full transcript drill-down.

## Quick start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend dev)

### 1. Environment

```bash
cp .env.example .env
# Edit SECRET_KEY, GROQ_API_KEY, Telnyx keys as needed
```

### 2. Backend + Database

```bash
docker compose up -d
```

API: http://localhost:8000 — Docs: http://localhost:8000/docs

Migrations run automatically on container start.

After backend code changes:

```bash
docker compose up -d --force-recreate api
```

### 3. Frontend

```bash
cd frontend
cp ../.env.example .env.local   # optional; defaults to localhost:8000
npm install
npm run dev
```

App: http://localhost:3000

### 4. Run tests (same as CI)

```bash
docker compose exec api python -m unittest discover -s tests -v
```

## Groq AI setup

1. Create an API key at [Groq Console](https://console.groq.com/).
2. Add to `.env`:
   ```bash
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

## Telnyx voice setup

1. Create an account at [Telnyx Mission Control](https://portal.telnyx.com/).
2. **API Keys** → create a key → `TELNYX_API_KEY`.
3. Copy **Account SID** → `TELNYX_ACCOUNT_SID`.
4. **Keys & Credentials → Public Key** → `TELNYX_PUBLIC_KEY` (webhook verification).
5. **Numbers** → buy a number → assign to a **TeXML Application**:
   - Voice URL: `https://your-api/api/v1/voice/inbound`
6. Optional SMS: create a **Messaging Profile** → `TELNYX_MESSAGING_PROFILE_ID`.
7. Add to `.env`:
   ```bash
   TELNYX_API_KEY=KEY...
   TELNYX_PUBLIC_KEY=...
   TELNYX_ACCOUNT_SID=...
   TELNYX_PHONE_NUMBER=+1...
   TELNYX_MESSAGING_PROFILE_ID=...   # optional
   PUBLIC_API_URL=https://your-ngrok-or-api-url
   VOICE_MODE=gather
   ```
8. In app **Settings**, set the same phone number and an escalation phone.

For local dev: `ngrok http 8000` and set `PUBLIC_API_URL` to the ngrok HTTPS URL.

## Email setup (booking confirmations + escalation alerts)

When SMTP is not configured, emails are **logged only** (dev mode). With SMTP configured, the app sends:

- **Booking confirmation** to the customer (when they have an email on file)
- **Escalation alert** to the business owner account email (fallback when owner SMS fails)

Add to `.env` (works with SendGrid, Mailgun, Amazon SES SMTP relay, etc.):

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG...
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_USE_TLS=true
```

## Stripe billing setup

1. Create two recurring Prices in [Stripe Dashboard](https://dashboard.stripe.com/products) (Starter $49/mo, Pro $99/mo).
2. Add to `.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_STARTER=price_...
   STRIPE_PRICE_PRO=price_...
   FRONTEND_URL=http://localhost:3000
   ```
3. Webhook endpoint: `https://your-api/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

New accounts get a **14-day free trial** on Starter limits.

## Development phases

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | **Done** | Database, auth, dashboard shell |
| 2 | **Done** | CRM + appointments API & UI |
| 3 | **Done** | AI text receptionist (Groq + tools) |
| 4 | **Done** | Voice calling (Telnyx TeXML + speech gather) |
| 5 | **Done** | Stripe billing + usage limits |
| 6 | **Done** | Onboarding wizard + unified inbox |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account + default business |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/auth/me` | Current user |
| GET/PATCH | `/api/v1/business` | Business profile |
| GET | `/api/v1/dashboard` | Dashboard summary |
| GET | `/api/v1/conversations` | Inbox list (calls, chats, SMS) |
| GET | `/api/v1/conversations/{id}` | Transcript + lead card + tool activity |
| GET/POST | `/api/v1/customers` | CRM |
| GET/POST | `/api/v1/appointments` | Calendar |
| GET | `/api/v1/appointments/availability` | Available slots |
| POST | `/api/v1/receptionist/chat` | Dashboard AI receptionist preview |
| POST/GET | `/api/v1/voice/inbound` | Telnyx inbound call webhook |
| POST/GET | `/api/v1/voice/gather` | Telnyx speech gather callback |
| POST | `/api/v1/voice/status` | Call status callback |
| POST/GET | `/api/v1/sms/inbound` | Telnyx SMS webhook |
| GET | `/api/v1/billing/status` | Subscription + usage |
| POST | `/api/v1/billing/checkout` | Stripe Checkout |
| POST | `/api/v1/billing/portal` | Stripe Customer Portal |
| GET | `/api/v1/onboarding/status` | Setup checklist |

Public customer web chat: `/chat/{slug}` (see `api/public.py`).

## Dashboard pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Overview, stats, recent conversations |
| `/dashboard/conversations` | **Inbox** — all customer conversations |
| `/dashboard/conversations/{id}` | Transcript, lead summary, tool activity |
| `/dashboard/receptionist` | Test AI receptionist (text chat) |
| `/dashboard/customers` | CRM |
| `/dashboard/calendar` | Appointments |
| `/dashboard/settings` | Phone, hours, escalation, AI instructions |
| `/dashboard/billing` | Stripe plan + usage |

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── ai/           # Groq agent, tools, prompts
│   │   ├── domain/       # Business rules (no HTTP deps)
│   │   ├── services/     # CRM, calendar, notifications, inbox
│   │   ├── voice/        # Telnyx TeXML, STT, gather flow
│   │   └── models/       # SQLAlchemy ORM
│   └── tests/            # Spec tests (run in CI)
├── frontend/
│   └── src/app/dashboard/
├── .github/workflows/ci.yml
└── docker-compose.yml
```

See `backend/app/ARCHITECTURE.md` and `HANDOVER.md` for agent handover notes.

## Deployment notes

Full runbook: **[DEPLOY.md](DEPLOY.md)** (VPS + Vercel + webhooks + manual checklist).

### macOS / Linux (local)

```bash
make setup
make dev-scheduler   # optional reminders cron
make frontend
make test
```

### Production (summary)

**Everything on one VPS (simplest):**

1. VPS **4 vCPU / 8 GB RAM / 80 GB SSD**
2. DNS: `app.` and `api.` → VPS IP
3. `cp .env.production.example .env` → fill values
4. `./scripts/prod-up.sh --all`

**Split setup:** API (+ optional frontend) on VPS, managed Postgres or Vercel — see **[DEPLOY.md](DEPLOY.md)**.

### Windows (local)

Use Docker Desktop — same as Quick start above (`docker compose up -d`). For production deploy, use a Linux VPS or WSL2.

- **CI**: GitHub Actions runs backend tests + frontend lint/build on push to `main`.
