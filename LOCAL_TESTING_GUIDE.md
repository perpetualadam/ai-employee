# Local Testing Guide — AI Employee

How to clone, run, and test the app on your own PC (Linux or Windows), including Telnyx phone number setup for US and UK.

---

## Can I test from GitHub directly?

**No.** GitHub hosts the code and runs CI — it does not run the app for you.

To test the full product you must get the repo onto a machine with:

- **Docker Desktop** (backend + database)
- **Node.js 20+** (frontend)
- **Git**

Options:

| Method | Works? |
|--------|--------|
| View code on github.com | Yes (read only) |
| GitHub Actions CI | Yes (automated tests only) |
| Clone to your PC and run locally | **Yes — this is what you need** |
| GitHub Codespaces | Yes (if you enable it — same commands as Linux below) |

### Which branch?

| Branch | Contents |
|--------|----------|
| `main` | Stable baseline |
| `cursor/fix-region-trade-intake-912a` | Latest UK/region fixes, trade intake questions, voice locale ([PR #2](https://github.com/perpetualadam/ai-employee/pull/2)) |

To test UK number provisioning and region fixes, checkout the fix branch until it is merged.

---

## Prerequisites

Install on your PC before starting:

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. [Node.js 20+](https://nodejs.org/)
3. [Git](https://git-scm.com/downloads)
4. [Groq API key](https://console.groq.com/) — **required** for AI chat
5. [Telnyx account](https://portal.telnyx.com/) — only for voice, SMS, and phone provisioning
6. [ngrok](https://ngrok.com/) — only for local voice testing (Telnyx needs a public HTTPS webhook)

---

## Quick start — Linux (bash)

```bash
# 1. Clone the repo
git clone https://github.com/perpetualadam/ai-employee.git
cd ai-employee

# 2. Use the branch with UK/region fixes (until merged to main)
git checkout cursor/fix-region-trade-intake-912a

# 3. Create environment file
cp .env.example .env

# 4. Edit .env — minimum required for chat testing:
#    GROQ_API_KEY=gsk_your_key_here
nano .env   # or: code .env

# 5. Start backend + PostgreSQL
docker compose up -d
docker compose exec api alembic upgrade head

# 6. Run automated tests (same as CI — expect 150 passing)
docker compose exec api python -m unittest discover -s tests -v

# 7. Optional: multi-trade smoke test (includes UK gas engineer)
docker compose exec api python scripts/p0_trade_qa.py

# 8. Start frontend (new terminal tab)
cd frontend
npm install
npm run dev
```

**Open in browser:**

| URL | What |
|-----|------|
| http://localhost:3000 | Web app (register, onboarding, dashboard) |
| http://localhost:8000/docs | API documentation |
| http://localhost:8000/health | Health check |

---

## Quick start — Windows (PowerShell)

```powershell
# 1. Clone the repo
git clone https://github.com/perpetualadam/ai-employee.git
cd ai-employee

# 2. Use the branch with UK/region fixes (until merged to main)
git checkout cursor/fix-region-trade-intake-912a

# 3. Create environment file
Copy-Item .env.example .env

# 4. Edit .env — minimum required for chat testing:
#    GROQ_API_KEY=gsk_your_key_here
notepad .env

# 5. Start backend + PostgreSQL
docker compose up -d
docker compose exec api alembic upgrade head

# 6. Run automated tests (expect 150 passing)
docker compose exec api python -m unittest discover -s tests -v

# 7. Optional: UK gas engineer smoke test only
docker compose exec api python scripts/p0_trade_qa.py gas_engineer

# 8. Start frontend (new PowerShell window)
cd frontend
npm install
npm run dev
```

Same URLs: http://localhost:3000 and http://localhost:8000/docs

---

## What you can test without Telnyx

| Test | Telnyx needed? | Groq needed? |
|------|----------------|--------------|
| Unit tests (`unittest discover`) | No | No (CI uses dummy key) |
| `p0_trade_qa.py` onboarding/API checks | No | No |
| Register + onboarding wizard | No | No |
| Dashboard text chat / booking | No | **Yes** |
| Voice phone calls | **Yes** | Yes |
| In-app phone number provisioning | **Yes** | No |
| SMS confirmations | **Yes** | No |

---

## Manual UK testing (text chat — no phone number needed)

1. Register a new account at http://localhost:3000
2. Onboarding step 1:
   - **Trade:** Gas engineer / heating
   - **Country:** United Kingdom
   - Timezone should auto-set to `Europe/London` and currency to `GBP`
3. Complete onboarding (services + phone step can be skipped for chat-only test)
4. Go to **Dashboard → Receptionist**
5. Try these messages:

| You say | Expected |
|---------|----------|
| My boiler won't start and there's no heating | AI asks trade-relevant follow-ups, then name/address |
| I smell gas in the kitchen | Mentions gas emergency; UK compliance references **0800 111 999** |
| 10 Downing Street, London, SW1A 2AA | Accepts UK postcode format in address hints |

Repeat with **Plumbing + United States** for US address/ZIP validation.

---

## Telnyx setup (full guide)

Telnyx provides voice calls and SMS. You need a Telnyx account before voice or phone provisioning works.

### Step 1 — Create a Telnyx account

1. Go to [https://portal.telnyx.com/](https://portal.telnyx.com/)
2. Sign up and verify your email
3. Add a payment method (required to purchase numbers, even for testing)
4. Complete any **identity / address verification** Telnyx requests — UK and some EU numbers often require this before purchase

### Step 2 — Create an API key

1. In Mission Control: **API Keys** (left menu)
2. Click **Create API Key**
3. Copy the key — you will not see it again
4. Add to `.env`:

```bash
TELNYX_API_KEY=KEYxxxxxxxxxxxxxxxx
```

### Step 3 — Copy Account SID and Public Key

1. **Account Settings** → copy **Account SID**:

```bash
TELNYX_ACCOUNT_SID=your_account_sid
```

2. **Keys & Credentials → Public Key** → copy the Ed25519 public key:

```bash
TELNYX_PUBLIC_KEY=your_public_key
```

The public key is used to verify inbound webhooks from Telnyx (voice/SMS).

### Step 4 — Create a TeXML Application (voice connection)

This is the "connection" that routes inbound calls to your API.

1. Mission Control → **Voice** → **TeXML Applications** (or **Call Control → TeXML Apps**)
2. Click **Create TeXML Application**
3. Set:
   - **Name:** `AI Employee Dev` (any name)
   - **Voice URL:** `https://YOUR-PUBLIC-URL/api/v1/voice/inbound`
     - For local dev this is your **ngrok HTTPS URL** (see Step 8 below)
     - Example: `https://abc123.ngrok-free.app/api/v1/voice/inbound`
   - **Voice method:** `GET` or `POST` (app supports both)
4. Save and copy the **Connection ID** (also called Application ID / TeXML Connection ID)

```bash
TELNYX_TEXML_CONNECTION_ID=your_connection_id
```

> **Important:** The Voice URL must be publicly reachable. `http://localhost:8000` will not work for real inbound calls from Telnyx.

### Step 5 — Create a Messaging Profile (SMS — optional but recommended)

1. Mission Control → **Messaging** → **Messaging Profiles**
2. Click **Create Profile**
3. Set inbound webhook URL:

```
https://YOUR-PUBLIC-URL/api/v1/sms/inbound
```

4. Copy the **Messaging Profile ID**:

```bash
TELNYX_MESSAGING_PROFILE_ID=your_messaging_profile_id
```

### Step 6 — Add Telnyx vars to `.env`

Full minimum set for voice + in-app provisioning:

```bash
# Telnyx
TELNYX_API_KEY=KEY...
TELNYX_ACCOUNT_SID=...
TELNYX_PUBLIC_KEY=...
TELNYX_TEXML_CONNECTION_ID=...
TELNYX_MESSAGING_PROFILE_ID=...
PUBLIC_API_URL=https://your-ngrok-url.ngrok-free.app
VOICE_MODE=gather

# Optional: lower-latency voice (requires DEEPGRAM_API_KEY + stream mode)
# VOICE_MODE=stream
# DEEPGRAM_API_KEY=...
```

Restart the API after editing `.env`:

**Linux:**
```bash
docker compose up -d --force-recreate api
```

**Windows:**
```powershell
docker compose up -d --force-recreate api
```

---

## Registering a phone number on Telnyx

There are **two ways** to get a number into the app.

### Option A — In-app provisioning (recommended)

The app buys and configures the number automatically during onboarding **Step 4: Phone**.

**Requirements:**

- `TELNYX_API_KEY` set
- `TELNYX_TEXML_CONNECTION_ID` set
- `TELNYX_MESSAGING_PROFILE_ID` set (for SMS on that number)
- Telnyx account verified for the target country (especially **GB**)

**Steps:**

1. Complete onboarding steps 1–3 with the correct **Country** first (country drives number search)
2. On **Step 4: Phone**, use the search panel:

| Country | Search field | Example |
|---------|--------------|---------|
| **US** | Area code (3 digits) | `614` |
| **UK (GB)** | City / area (text) | `London` |
| **Australia** | STD area code | `02` |
| **New Zealand** | No filter — country-wide search | (leave blank, click Search) |

3. Click **Search numbers** → pick a result → **Get this number**
4. The app will:
   - Purchase the number via Telnyx API
   - Assign it to your TeXML connection
   - Attach the messaging profile
   - Save it on your business record

**UK notes:**

- Select **United Kingdom** as country **before** searching
- Search with a city name like `London` or `Manchester` — **not** a 3-digit US-style area code
- If search returns no results, your Telnyx account may need UK regulatory approval — complete verification in the Telnyx portal under **Numbers → Regulatory Requirements**

**US notes:**

- Search with a 3-digit area code (e.g. `415`, `614`)
- Release old US numbers in Telnyx portal if you are switching to UK

### Option B — Buy manually in Telnyx portal

Use this if in-app provisioning is unavailable or you already own a number.

1. Mission Control → **Numbers** → **Buy Numbers**
2. Select country:
   - **United States** → pick area code / number
   - **United Kingdom** → complete any regulatory bundle Telnyx requires, then search by city/area
3. Purchase the number
4. Assign the number to your **TeXML Application** (connection) from Step 4 above
5. Assign the **Messaging Profile** for SMS
6. In the app onboarding **Step 4**, use **"Or enter your own Telnyx number"** and paste the E.164 number (e.g. `+447911123456`)
7. Click **Save phone number**

### Releasing a number

To switch from US to UK:

1. **Telnyx portal** → **Numbers** → select the US number → **Release/Delete**
2. In the app, provision or manually enter the new `+44` number
3. Each business can only have one provisioned number — release the old one first if migrating

---

## Local voice testing with ngrok

Telnyx cannot call `localhost`. You need a public HTTPS tunnel.

### Linux

```bash
# Terminal 1 — keep Docker running
docker compose up -d

# Terminal 2 — start ngrok
ngrok http 8000
```

Copy the **https** forwarding URL (e.g. `https://abc123.ngrok-free.app`).

### Windows (PowerShell)

```powershell
# Terminal 1 — keep Docker running
docker compose up -d

# Terminal 2 — start ngrok
ngrok http 8000
```

### Update config

1. Set in `.env`:

```bash
PUBLIC_API_URL=https://abc123.ngrok-free.app
```

2. Update Telnyx TeXML Application **Voice URL** to:

```
https://abc123.ngrok-free.app/api/v1/voice/inbound
```

3. Update Messaging Profile **Webhook URL** to:

```
https://abc123.ngrok-free.app/api/v1/sms/inbound
```

4. Restart API:

```bash
docker compose up -d --force-recreate api
```

### Test a call

1. Finish onboarding with a provisioned number
2. Call that number from your mobile
3. Expect: trade-specific greeting → beep → speak your problem
4. Watch logs:

```bash
docker compose logs -f api
```

**UK voice:** GB businesses use `en-GB` TTS (Polly.Amy). US businesses use `en-US`.

---

## Automated test commands reference

### All unit tests

**Linux:**
```bash
docker compose exec api python -m unittest discover -s tests -v
```

**Windows:**
```powershell
docker compose exec api python -m unittest discover -s tests -v
```

### Multi-trade QA (plumbing US + gas engineer GB + mobile mechanic US)

**Linux:**
```bash
docker compose exec api python scripts/p0_trade_qa.py
```

**Windows:**
```powershell
docker compose exec api python scripts/p0_trade_qa.py
```

### UK gas engineer only

**Linux:**
```bash
docker compose exec api python scripts/p0_trade_qa.py gas_engineer
```

**Windows:**
```powershell
docker compose exec api python scripts/p0_trade_qa.py gas_engineer
```

### Without Docker (developers)

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. GROQ_API_KEY=test-dummy python3 -m unittest discover -s tests -v
```

---

## Manual text chat scripts

See also `P0_QA.md` for full checklists.

### Plumbing (US)

| Turn | You say |
|------|---------|
| 1 | I have no hot water |
| 2 | Brian Smith |
| 3 | 123 Main Street, Columbus, OH 43215 |
| 4 | Yes that's correct |
| 5 | Tomorrow |
| 6 | The first slot |
| 7 | No thanks, bye |

### Gas engineer (GB)

| Turn | You say |
|------|---------|
| 1 | My boiler won't start and there's no heating |
| 2 | (follow AI intake questions) |
| 3 | James Wilson |
| 4 | 42 High Street, Manchester, M1 1AE |
| 5 | Yes that's correct |
| 6–7 | Book a slot |

**Emergency test:** say *"I smell gas"* — AI should escalate and mention UK gas emergency line.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Chat does not respond | Set `GROQ_API_KEY` in `.env`, restart API |
| `docker compose` not found | Install Docker Desktop; on Windows use PowerShell not CMD |
| Phone search returns nothing (UK) | Complete Telnyx UK regulatory verification; try different city |
| Phone search uses wrong filter | Ensure **Country** is set in onboarding before step 4 |
| Inbound calls fail / no greeting | Check `PUBLIC_API_URL` matches ngrok URL; verify TeXML Voice URL |
| Webhook signature errors | Ensure `TELNYX_PUBLIC_KEY` matches Telnyx portal |
| `can_search: false` in phone panel | Set `TELNYX_API_KEY` + `TELNYX_TEXML_CONNECTION_ID` |
| Port 3000 or 8000 in use | Stop other apps or change ports in `docker-compose.yml` / Next.js |

**View API logs:**

```bash
docker compose logs -f api
```

```powershell
docker compose logs -f api
```

---

## After testing — cleanup

- **Dashboard → Calendar** — cancel test appointments
- **Telnyx portal** — release test numbers you no longer need
- Stop services:

```bash
docker compose down
```

```powershell
docker compose down
```

---

## Related docs

| File | Purpose |
|------|---------|
| `README.md` | Architecture and quick start |
| `P0_QA.md` | Pre-deploy manual QA checklist |
| `backend/TESTING.md` | Full test strategy |
| `LAUNCH_CHECKLIST.md` | Production launch tasks |
| `.env.example` | All environment variables |

---

## Summary

1. **Clone** the repo to your PC — you cannot run the app on GitHub alone
2. Checkout **`cursor/fix-region-trade-intake-912a`** for latest UK fixes
3. **Chat testing** needs only Docker + Groq key
4. **Voice/SMS/numbers** need Telnyx + ngrok for local dev
5. **UK numbers:** set country to GB, search by city (`London`), complete Telnyx UK verification if required
6. **US numbers:** search by 3-digit area code; release US number before switching to UK
