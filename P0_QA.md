# P0 Local QA — Multi-Trade

Run this before deploy. Three trades: **plumbing (US)**, **gas engineer (GB)**, **mobile mechanic (US)**.

## 1. Start stack

```powershell
docker compose up -d
docker compose exec api alembic upgrade head
cd frontend && npm run dev
```

Ensure `GROQ_API_KEY` is set in `.env` for text chat tests.

## 2. Automated smoke (API)

```powershell
docker compose exec api python scripts/p0_trade_qa.py
```

**Expect:** all onboarding/seed checks PASS for each trade. Chat booking may need manual completion in the dashboard (AI turns vary).

Subset only:

```powershell
docker compose exec api python scripts/p0_trade_qa.py plumbing gas_engineer
```

## 3. Manual text chat — per trade

Use a **fresh account** or change industry in onboarding for each trade.

### Plumbing (US)

1. Register / onboarding → Trade: **Plumbing**, Country: **United States**
2. Step 2 → confirm services: Drain cleaning, Water heater, Emergency leak
3. **Dashboard → Receptionist** (new session each time):

| Turn | You say |
|------|---------|
| 1 | I have no hot water |
| 2 | Brian Smith |
| 3 | 123 Main Street, Columbus, OH 43215 |
| 4 | Yes that's correct |
| 5 | Tomorrow |
| 6 | The first slot |
| 7 | No thanks, bye |

**Pass:** `book_appointment` in tool log, appointment on **Calendar**, clean goodbye.

### Gas engineer (GB)

1. Trade: **Gas engineer / heating**, Country: **United Kingdom**
2. Services preview: Boiler service, Gas appliance repair, …
3. Receptionist problem: *"My boiler won't start and there's no heating"*
4. Same intake → book flow (use a UK-style address if testing GB hints)

**Pass:** AI mentions heating/boiler context; emergency if you say *"I smell gas"*.

### Mobile mechanic (US)

1. Trade: **Mobile mechanic**, Country: **United States**
2. Problem: *"My car won't start, battery might be dead"*
3. Complete booking flow

**Pass:** service type matches roadside/battery; greeting examples mention car/won't start.

## 4. Voice (manual — needs Telnyx)

1. `ngrok http 8000` → set `PUBLIC_API_URL` in `.env` → restart API
2. Telnyx voice URL → `{PUBLIC_API_URL}/api/v1/voice/inbound`
3. Call business number after each trade setup
4. **Pass:** trade-specific greeting after beep; no signature errors in `docker compose logs -f api`

## 5. Cleanup

- **Dashboard → Calendar** — cancel test appointments
- Optional: delete QA users created by `p0_trade_qa.py`

## Pass criteria summary

| Check | Automated | Manual |
|-------|-----------|--------|
| Trade catalog + seed | `p0_trade_qa.py` | Onboarding UI |
| Services in DB | `p0_trade_qa.py` | Onboarding step 2 |
| Text book flow | Partial | Receptionist |
| Voice call | — | Phone |
| Calendar entry | Partial | Calendar UI |
