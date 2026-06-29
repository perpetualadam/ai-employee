# AI Employee

AI receptionist SaaS for trade businesses. Answers calls, qualifies leads, books jobs, sends confirmations, and updates a simple CRM.

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
              │ PostgreSQL │            │  Groq API     │          │ Twilio/Telnyx │
              │ (multi-    │            │  (Phase 3)    │          │ (Phase 4)     │
              │  tenant)   │            └───────────────┘          └───────────────┘
              └───────────┘
```

### Multi-tenancy

Every tenant-scoped table includes `business_id`. API routes resolve the authenticated user's business and filter all queries by that ID. Designed to scale to thousands of businesses on a single PostgreSQL instance with proper indexing.

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
| `call_logs` | Phone call history |
| `ai_activity_logs` | AI tool call audit trail |

### AI & Voice (prepared, not yet wired)

- `backend/app/ai/provider.py` — swappable AI provider interface (Groq first)
- `backend/app/ai/tools.py` — receptionist tool definitions
- `backend/app/voice/provider.py` — swappable voice provider (Twilio first)

## Quick start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend dev)

### 1. Environment

```bash
cp .env.example .env
# Edit SECRET_KEY and other values as needed
```

### 2. Backend + Database

```bash
docker compose up -d
```

API runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs` (debug mode).

Migrations run automatically on container start.

### 3. Frontend

```bash
cd frontend
cp ../.env.example .env.local   # or set NEXT_PUBLIC_API_URL
npm run dev
```

App runs at `http://localhost:3000`.

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
3. Add webhook endpoint: `https://your-api/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
4. Enable Stripe Customer Portal in Stripe Dashboard (Settings → Billing → Customer portal).

New accounts get a **14-day free trial** on the Starter plan limits. AI receptionist and voice calls require an active trial or subscription.

## Development phases

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | **Done** | Database, auth, dashboard shell |
| **2** | **Done** | CRM + appointments API & UI |
| **3** | **Done** | AI text receptionist (Groq + tools) |
| **4** | **Done** | Voice calling (Twilio + STT/TTS) |
| **5** | **Done** | Stripe billing + usage limits |
| **6** | **Done** | Onboarding wizard + checklist + empty states |

## API endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account + default business |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/business` | Business profile |
| PATCH | `/api/v1/business` | Update profile |
| GET | `/api/v1/dashboard` | Dashboard summary |
| GET/POST | `/api/v1/customers` | List / create customers |
| GET/PATCH/DELETE | `/api/v1/customers/{id}` | Customer CRUD |
| GET/POST | `/api/v1/jobs` | List / create jobs |
| GET/PATCH/DELETE | `/api/v1/jobs/{id}` | Job CRUD |
| GET/POST | `/api/v1/appointments` | List / book appointments |
| GET | `/api/v1/appointments/availability` | Available slots for a date |
| PATCH | `/api/v1/appointments/{id}` | Reschedule / update |
| POST | `/api/v1/appointments/{id}/cancel` | Cancel appointment |
| POST | `/api/v1/receptionist/chat` | Chat with AI receptionist |
| POST | `/api/v1/voice/inbound` | Twilio inbound call webhook |
| POST | `/api/v1/voice/gather` | Twilio speech recognition callback |
| POST | `/api/v1/voice/status` | Twilio call status callback |
| WS | `/api/v1/voice/stream` | Twilio Media Streams (real-time STT) |
| GET | `/api/v1/billing/status` | Subscription status and usage |
| POST | `/api/v1/billing/checkout` | Start Stripe Checkout |
| POST | `/api/v1/billing/portal` | Stripe Customer Portal |
| POST | `/api/v1/billing/webhook` | Stripe webhook |
| GET | `/api/v1/onboarding/status` | Setup checklist progress |
| POST | `/api/v1/onboarding/complete` | Mark onboarding done |
| POST | `/api/v1/onboarding/seed-defaults` | Add default services & rules |
| POST | `/api/v1/onboarding/sample-data` | Add demo customer & appointment |

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── ai/           # Groq provider, tools, agent
│   │   ├── core/         # Auth, deps, logging
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic DTOs
│   │   ├── services/     # Business logic
│   │   └── voice/        # Voice provider (Phase 4)
│   └── alembic/          # Database migrations
├── frontend/
│   └── src/
│       ├── app/          # Next.js pages
│       ├── components/   # UI components
│       └── lib/          # API client, auth helpers
└── docker-compose.yml
```

## Deployment notes

- **Frontend**: Deploy to Vercel. Set `NEXT_PUBLIC_API_URL` to your API URL.
- **Backend**: Deploy Docker container to any VPS (Hetzner, DigitalOcean, etc.).
- **Database**: Managed PostgreSQL or the included Docker volume for MVP.
