# Deployment guide (P1)

Production deployment for **AI Employee**: backend on a Linux VPS with Docker + Caddy (HTTPS), frontend on Vercel, managed PostgreSQL recommended.

---

## Platform support

| Platform | Local dev | Production |
|----------|-----------|------------|
| **macOS** | Docker Desktop + `make setup` | VPS deploy (same as Linux) |
| **Linux** | Docker Engine + `make setup` | VPS deploy (recommended) |
| **Windows** | Docker Desktop + `docker compose up -d` | Use WSL2 or deploy from macOS/Linux VPS |

All shell scripts use bash and LF line endings (`.gitattributes` enforces this).

---

## What is already in the repo

| Artifact | Purpose |
|----------|---------|
| `docker-compose.yml` | Local dev (hot reload, Postgres included) |
| `docker-compose.prod.yml` | Production API + Caddy TLS + optional scheduler; **`migrate` service runs `alembic upgrade head` before API starts** |
| `deploy/Caddyfile` | Automatic HTTPS (Let's Encrypt) |
| `.env.production.example` | Production env template |
| `Makefile` + `scripts/*.sh` | macOS/Linux commands |
| `frontend/vercel.json` | Vercel build config |
| `/health/live`, `/health/ready` | Load balancer / Docker health checks |

---

## Local development (macOS / Linux)

```bash
git clone https://github.com/perpetualadam/ai-employee.git
cd ai-employee
make setup          # creates .env, starts db + api
make dev-scheduler  # optional: appointment reminder cron
make frontend       # separate terminal: Next.js on :3000
make test           # run backend spec tests
```

**Windows (Docker Desktop):**

```powershell
copy .env.example .env
docker compose up -d
cd frontend; npm install; npm run dev
```

---

## Production architecture

### Option A — Everything on one VPS (recommended for simplicity)

```
                         ┌─────────────────────────────────────┐
  Users ───────────────► │              Linux VPS              │
                         │  ┌─────────┐  ┌─────────┐  ┌──────┐ │
                         │  │  Caddy  │  │ Next.js │  │ API  │ │
                         │  │  :443   │──│  :3000  │  │:8000 │ │
                         │  └────┬────┘  └─────────┘  └──┬───┘ │
                         │       │                        │    │
                         │       │                   ┌────▼───┐ │
                         │       │                   │Postgres│ │
                         │       │                   └────────┘ │
                         └───────┼──────────────────────────────┘
                                 │
                    Groq / Telnyx / Stripe (external APIs)
```

```bash
./scripts/prod-up.sh --all
```

### Option B — Split (managed Postgres and/or Vercel frontend)

```
  Vercel (frontend) ──► Caddy on VPS (API) ──► Managed Postgres
```

See sections below if you prefer external database or Vercel for the frontend only.

---

## Full stack on one VPS

Best when you want **one bill, one server, full control**. Good for launch traffic if sized correctly.

### Server specs

| Launch interest | vCPU | RAM | Disk |
|-----------------|------|-----|------|
| Soft launch | 2 | 4 GB | 40 GB SSD |
| **Public launch / fair interest** | **4** | **8 GB** | **80 GB SSD** |
| Heavy spike headroom | 4–8 | 16 GB | 100 GB SSD |

Runs on the same box: **Caddy** (TLS) + **Next.js** + **FastAPI** (4 workers) + **Postgres** + **reminder scheduler**.

### DNS (both subdomains → same VPS IP)

| Record | Name | Value |
|--------|------|-------|
| A | `app.yourdomain.com` | VPS public IP |
| A | `api.yourdomain.com` | VPS public IP |

### Start

```bash
cp .env.production.example .env
# Set APP_DOMAIN, API_DOMAIN, POSTGRES_PASSWORD, secrets, API keys
chmod +x scripts/*.sh
./scripts/prod-up.sh --all
```

Open **https://app.yourdomain.com** — no Vercel needed.

---

## VPS deployment

### 1. Server requirements

- Ubuntu 22.04+ or Debian 12+ (or any Linux with Docker)
- **Full stack (`--all`):** 4 vCPU, **8 GB RAM**, 80 GB SSD recommended for launch
- **API only (external DB):** 2 vCPU, 4 GB RAM minimum
- Ports **80** and **443** open
- A domain name you control

### 2. Install Docker on the VPS

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# log out and back in
docker compose version
```

### 3. Clone and configure

```bash
git clone https://github.com/perpetualadam/ai-employee.git
cd ai-employee
cp .env.production.example .env
nano .env   # fill every required value (see template comments)
```

Generate secrets:

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 24   # CRON_SECRET
```

**Critical `.env` values:**

| Variable | Example |
|----------|---------|
| `APP_DOMAIN` | `app.yourdomain.com` |
| `API_DOMAIN` | `api.yourdomain.com` |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com/api/v1` |
| `ACME_EMAIL` | `you@yourdomain.com` |
| `PUBLIC_API_URL` | `https://api.yourdomain.com` |
| `FRONTEND_URL` | `https://app.yourdomain.com` |
| `CORS_ORIGINS` | `https://app.yourdomain.com` |
| `ALLOWED_HOSTS` | `api.yourdomain.com` |
| `DATABASE_URL` | `postgresql://aiemployee:PASSWORD@db:5432/aiemployee` (with `--all`) |
| `POSTGRES_PASSWORD` | strong password (with `--all`) |
| `DEBUG` | `false` |
| `UVICORN_WORKERS` | `4` for launch traffic |
| `STORAGE_LOCAL_PATH` | `/app/storage` (matches prod Docker volume; do not commit upload files) |

### File storage (verification uploads)

Uploads (e.g. regulatory documents) are stored on disk by the **local storage plugin**, not in Postgres. The folder is **created automatically** on first upload.

| Environment | Behavior |
|-------------|----------|
| **Production (`docker-compose.prod.yml`)** | Docker volume `app_storage` → `/app/storage` — survives redeploys |
| **Local dev (`docker compose up`)** | `./backend/storage/` on your machine (bind-mounted via `./backend:/app`) |
| **Git** | Never commit `backend/storage/` — runtime data only |

Back up the `app_storage` volume with your VPS backups (same importance as Postgres for uploaded documents).

### 4. DNS

Create **A records** for `app.yourdomain.com` and `api.yourdomain.com` → VPS public IP.

Wait for DNS propagation before starting Caddy (Let's Encrypt needs this).

### 5. Start production stack

**Everything on one VPS (app + API + Postgres):**

```bash
chmod +x scripts/*.sh
./scripts/prod-up.sh --all
```

**App + API on VPS, managed Postgres elsewhere:**

```bash
# DATABASE_URL=postgresql://...?sslmode=require in .env
./scripts/prod-up.sh
```

### 6. Verify

```bash
docker compose -f docker-compose.prod.yml ps
curl -s https://api.yourdomain.com/health/ready
curl -s https://api.yourdomain.com/health
```

---

## Frontend deployment (Vercel — optional)

Skip this section if you use **`./scripts/prod-up.sh --all`** (frontend runs in Docker on your VPS).

1. Import the GitHub repo at [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add environment variable:

   | Name | Value |
   |------|-------|
   | `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com/api/v1` |

4. Deploy. Note the Vercel URL (e.g. `app.yourdomain.com`).
5. Ensure `CORS_ORIGINS` and `FRONTEND_URL` in VPS `.env` match the Vercel URL.

Optional: add a custom domain in Vercel → `app.yourdomain.com` (CNAME to Vercel).

---

## External webhooks (after HTTPS is live)

Point these to your **production** `PUBLIC_API_URL`:

| Provider | URL | Notes |
|----------|-----|-------|
| **Telnyx TeXML app** | `{PUBLIC_API_URL}/api/v1/voice/inbound` | Voice URL on TeXML connection |
| **Telnyx gather** | `{PUBLIC_API_URL}/api/v1/voice/gather` | Set on TeXML app |
| **Telnyx SMS** | `{PUBLIC_API_URL}/api/v1/sms/inbound` | Messaging profile webhook |
| **Stripe** | `{PUBLIC_API_URL}/api/v1/billing/webhook` | Events: checkout, subscription, invoice |

Set `TELNYX_TEXML_CONNECTION_ID` in `.env` for per-tenant phone provisioning.

---

## Database backups

**Bundled Postgres on VPS:**

```bash
make backup
# files saved to backups/
```

**Managed Postgres:** use your provider's automated backups (Neon/Supabase/RDS). Optionally:

```bash
pg_dump "$DATABASE_URL" | gzip > backups/manual.sql.gz
```

**Restore (bundled db only):**

```bash
make restore FILE=backups/aiemployee_20260101_120000.sql.gz
```

---

## Operations cheat sheet

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f api caddy scheduler

# Restart API after .env change
docker compose -f docker-compose.prod.yml up -d --build api

# Migrations run automatically on `./scripts/prod-up.sh` and before each API start.
# To apply migrations only (e.g. after pulling new code):
make migrate-prod
# or: ./scripts/migrate-prod.sh [--all]

# Stop everything
docker compose -f docker-compose.prod.yml down
```

---

## What you must do manually

These steps require your accounts, billing, DNS, and secrets — they cannot be automated from the repo.

### Accounts & billing

- [ ] **Domain registrar** — buy/configure `yourdomain.com`
- [ ] **VPS provider** — create a server (DigitalOcean, Hetzner, Linode, AWS EC2, etc.)
- [ ] **Vercel account** — connect GitHub repo, deploy `frontend/`
- [ ] **Managed Postgres** — create database (Neon, Supabase, RDS, etc.) and copy connection string
- [ ] **Groq** — create API key at [console.groq.com](https://console.groq.com/)
- [ ] **Telnyx** — account, API key, public key, TeXML connection, messaging profile, phone number(s)
- [ ] **Stripe** — account, products/prices, webhook endpoint, live keys when ready
- [ ] **SMTP** — SendGrid, Mailgun, SES, or similar (for email reminders + escalation)
- [ ] **Sentry** (optional) — create project, copy DSN

### DNS & networking

- [ ] **A record** — `api.yourdomain.com` → VPS IP
- [ ] **CNAME** (optional) — `app.yourdomain.com` → Vercel
- [ ] **Firewall** — allow ports 80, 443 on VPS; restrict 5432 (never expose Postgres publicly)

### Secrets & configuration

- [ ] Copy `.env.production.example` → `.env` on VPS and fill **all** values
- [ ] Generate `SECRET_KEY` and `CRON_SECRET` (`openssl rand -hex`)
- [ ] Set `DEBUG=false`, `ALLOWED_HOSTS=api.yourdomain.com`
- [ ] Set `NEXT_PUBLIC_API_URL` in **Vercel dashboard**
- [ ] Set `CORS_ORIGINS` and `FRONTEND_URL` to match Vercel URL

### Telnyx production setup

- [ ] Create TeXML Application with voice URL → `https://api.yourdomain.com/api/v1/voice/inbound`
- [ ] Copy TeXML **Connection ID** → `TELNYX_TEXML_CONNECTION_ID`
- [ ] Configure SMS inbound webhook → `https://api.yourdomain.com/api/v1/sms/inbound`
- [ ] Provision or assign phone number(s) in app Settings or via onboarding

### Stripe production setup

- [ ] Create live (or test) prices → `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`
- [ ] Webhook → `https://api.yourdomain.com/api/v1/billing/webhook`
- [ ] Copy webhook signing secret → `STRIPE_WEBHOOK_SECRET`

### Go-live verification

- [ ] `curl https://api.yourdomain.com/health/ready` returns `"status":"ok"`
- [ ] Register/login on Vercel frontend works
- [ ] Text chat booking flow completes
- [ ] Live voice call to Telnyx number completes booking
- [ ] SMS confirmation sends (requires `TELNYX_MESSAGING_PROFILE_ID`)
- [ ] Scheduler logs show `Reminders: checked=...` hourly
- [ ] Stripe checkout opens and webhook fires

### Ongoing ops

- [ ] Enable managed Postgres automated backups (or schedule `make backup`)
- [ ] Monitor Sentry / logs for errors
- [ ] Rotate secrets periodically
- [ ] P0 QA checklist in `HANDOVER.md`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Caddy won't get certificate | DNS not propagated; port 80 blocked; wrong `API_DOMAIN` |
| 403 from API | `ALLOWED_HOSTS` doesn't match request Host header |
| CORS errors in browser | `CORS_ORIGINS` missing Vercel URL (include `https://`, no trailing slash) |
| Scheduler 503 | `CRON_SECRET` unset with `DEBUG=false` |
| Telnyx signature failures | `TELNYX_PUBLIC_KEY` wrong; webhook URL must be HTTPS |
| DB connection failed | Check `DATABASE_URL`, SSL mode, firewall to managed Postgres |

---

See also: `README.md`, `HANDOVER.md`, `.env.production.example`.
