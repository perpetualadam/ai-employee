# AI Employee - Production Launch Checklist

**Target Launch Date**: _________  
**Last Updated**: 2026-07-14  
**Owner**: Product/Engineering Lead

---

## ✅ PRE-LAUNCH TASKS

### 🔐 **1. Security & Infrastructure** (ETA: 1-2 days)

- [ ] **Generate production SECRET_KEY**
  - [ ] Run: `openssl rand -hex 32`
  - [ ] Update `.env` with generated key
  - [ ] Verify key is NOT the default value
  - **Owner**: DevOps
  - **Acceptance**: SECRET_KEY ≠ "change-me-in-production"

- [ ] **Install rate limiting dependencies**
  - [ ] Run: `pip install slowapi==0.1.9`
  - [ ] Verify rate limiting on `/auth/login` (5/minute)
  - [ ] Verify rate limiting on `/auth/register` (3/hour)
  - **Owner**: Backend Dev
  - **Acceptance**: 429 response after exceeding limits

- [ ] **Configure Redis for rate limiting (production)**
  - [ ] Install Redis: `docker run -d --name redis -p 6379:6379 redis:7-alpine`
  - [ ] Update `app/core/rate_limit.py` storage_uri to Redis
  - [ ] Test rate limiting persists across API restarts
  - **Owner**: DevOps
  - **Acceptance**: Rate limits work after API restart

- [ ] **Set up production database**
  - [ ] Create PostgreSQL database (managed or self-hosted)
  - [ ] Update `DATABASE_URL` in `.env`
  - [ ] Migrations run automatically on deploy (`./scripts/prod-up.sh` or `make migrate-prod`); verify `/health/ready` after first deploy
  - **Owner**: DevOps
  - **Acceptance**: `/health/ready` returns `"ok"`

- [ ] **Configure CORS origins**
  - [ ] Set `CORS_ORIGINS` to production frontend URL
  - [ ] Remove `http://localhost:3000` from allowed origins
  - **Owner**: DevOps
  - **Acceptance**: Only production domain allowed

- [ ] **Configure trusted hosts**
  - [ ] Set `ALLOWED_HOSTS` to production API domain
  - [ ] Remove `*` wildcard
  - **Owner**: DevOps
  - **Acceptance**: Requests from unknown hosts rejected

### 🔌 **2. External Service Configuration** (ETA: 1-2 days)

- [ ] **Groq AI Configuration**
  - [ ] Create API key at https://console.groq.com/
  - [ ] Set `GROQ_API_KEY` in `.env`
  - [ ] Set `GROQ_MODEL=llama-3.3-70b-versatile`
  - [ ] Test: Send test message via `/receptionist/chat`
  - **Owner**: Engineering
  - **Acceptance**: AI responds to test message

- [ ] **Telnyx Voice & SMS Setup**
  - [ ] Create Telnyx account at https://portal.telnyx.com/
  - [ ] Generate API key → Set `TELNYX_API_KEY`
  - [ ] Copy Account SID → Set `TELNYX_ACCOUNT_SID`
  - [ ] Copy Public Key → Set `TELNYX_PUBLIC_KEY`
  - [ ] Purchase phone number
  - [ ] Create TeXML Application with Voice URL: `https://api.yourdomain.com/api/v1/voice/inbound`
  - [ ] Set SMS URL: `https://api.yourdomain.com/api/v1/sms/inbound`
  - [ ] Create Messaging Profile → Set `TELNYX_MESSAGING_PROFILE_ID`
  - [ ] Set `TELNYX_PHONE_NUMBER=+1...`
  - [ ] Set `PUBLIC_API_URL=https://api.yourdomain.com`
  - **Owner**: Product/Engineering
  - **Acceptance**: Test voice call + SMS delivery

- [ ] **Stripe Billing Setup**
  - [ ] Create Starter & Pro products at https://dashboard.stripe.com/products
  - [ ] Set `STRIPE_SECRET_KEY=sk_live_...`
  - [ ] Set `STRIPE_PRICE_STARTER=price_...`
  - [ ] Set `STRIPE_PRICE_PRO=price_...`
  - [ ] Configure webhook: `https://api.yourdomain.com/api/v1/billing/webhook`
  - [ ] Set `STRIPE_WEBHOOK_SECRET=whsec_...`
  - [ ] Add webhook events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`
  - [ ] Set `FRONTEND_URL=https://app.yourdomain.com`
  - **Owner**: Product/Finance
  - **Acceptance**: Test checkout flow end-to-end

- [ ] **Sentry Monitoring (Optional but Recommended)**
  - [ ] Create project at https://sentry.io/
  - [ ] Set `SENTRY_DSN=https://...`
  - [ ] Set `SENTRY_ENVIRONMENT=production`
  - [ ] Test: Trigger test error, verify in Sentry dashboard
  - [ ] Configure frontend: `NEXT_PUBLIC_SENTRY_DSN`
  - **Owner**: Engineering
  - **Acceptance**: Test error appears in Sentry

- [ ] **SMTP Email Configuration**
  - [ ] Choose provider (SendGrid, Mailgun, AWS SES)
  - [ ] Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
  - [ ] Set `SMTP_FROM_EMAIL=noreply@yourdomain.com`
  - [ ] Test: Book appointment, verify confirmation email
  - **Owner**: Engineering
  - **Acceptance**: Booking confirmation emails sent

### 🏗️ **3. Infrastructure Deployment** (ETA: 2-3 days)

- [ ] **VPS Setup (if self-hosting)**
  - [ ] Provision VPS (4 vCPU / 8 GB RAM / 80 GB SSD)
  - [ ] Install Docker: `curl -fsSL https://get.docker.com | sh`
  - [ ] Clone repository: `git clone https://github.com/perpetualadam/ai-employee.git`
  - [ ] Configure `.env` with all secrets
  - **Owner**: DevOps
  - **Acceptance**: Docker installed, repo cloned

- [ ] **DNS Configuration**
  - [ ] Add A record: `api.yourdomain.com` → VPS IP
  - [ ] Add A record: `app.yourdomain.com` → VPS IP (or Vercel)
  - [ ] Wait for propagation (up to 48 hours)
  - [ ] Verify: `dig api.yourdomain.com`
  - **Owner**: DevOps
  - **Acceptance**: DNS resolves to correct IP

- [ ] **SSL/TLS Setup (Caddy)**
  - [ ] Ensure ports 80 and 443 open on firewall
  - [ ] Deploy: `./scripts/prod-up.sh --all`
  - [ ] Verify Caddy obtains Let's Encrypt certificate
  - [ ] Test: `curl https://api.yourdomain.com/health`
  - **Owner**: DevOps
  - **Acceptance**: HTTPS works, no certificate errors

- [ ] **Frontend Deployment (Vercel)**
  - [ ] Connect GitHub repo to Vercel
  - [ ] Set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1`
  - [ ] Deploy production build
  - [ ] Verify: Visit `https://app.yourdomain.com`
  - **Owner**: Frontend Dev
  - **Acceptance**: Frontend loads, API calls work

### 🧪 **4. P0 Quality Assurance** (ETA: 2-3 days)

**Reference**: See `P0_QA.md` for detailed test scripts

- [ ] **Automated Smoke Tests**
  - [ ] Run: `docker compose exec api python scripts/p0_trade_qa.py`
  - [ ] Verify all 3 trades pass: plumbing, gas_engineer, mobile_mechanic
  - **Owner**: QA/Engineering
  - **Acceptance**: All automated checks pass

- [ ] **Text Chat Booking - Plumbing (US)**
  - [ ] Register new test account
  - [ ] Complete onboarding: Trade=Plumbing, Country=US
  - [ ] Navigate to Dashboard → Receptionist
  - [ ] Test conversation: "I have no hot water" → full booking flow
  - [ ] Verify: Appointment created in Calendar
  - [ ] Verify: SMS confirmation sent (if configured)
  - **Owner**: QA
  - **Acceptance**: Booking appears in calendar, clean conversation

- [ ] **Text Chat Booking - Gas Engineer (GB)**
  - [ ] New account or change industry
  - [ ] Trade=Gas engineer / heating, Country=GB
  - [ ] Test: "My boiler won't start"
  - [ ] Verify UK-specific compliance in prompts
  - [ ] Complete booking flow
  - **Owner**: QA
  - **Acceptance**: GB address hints shown, booking succeeds

- [ ] **Text Chat Booking - Mobile Mechanic (US)**
  - [ ] Trade=Mobile mechanic, Country=US
  - [ ] Test: "My car won't start, battery might be dead"
  - [ ] Complete booking flow
  - **Owner**: QA
  - **Acceptance**: Service type matches auto/battery

- [ ] **Live Voice Call Test**
  - [ ] Call production phone number from external phone
  - [ ] Verify: Trade-specific greeting plays
  - [ ] Complete voice booking flow
  - [ ] Verify: No errors in logs (`docker compose logs -f api`)
  - [ ] Verify: Appointment created
  - **Owner**: QA/Engineering
  - **Acceptance**: Voice call completes successfully

- [ ] **SMS Confirmation Test**
  - [ ] Complete booking via voice or text
  - [ ] Verify: Customer receives SMS confirmation
  - [ ] Verify: SMS contains appointment time + address
  - **Owner**: QA
  - **Acceptance**: SMS received within 30 seconds

- [ ] **Email Confirmation Test**
  - [ ] Book appointment with customer email provided
  - [ ] Verify: Booking confirmation email sent
  - [ ] Check spam folder if not received
  - **Owner**: QA
  - **Acceptance**: Email delivered successfully

- [ ] **Bulk Calendar Cleanup**
  - [ ] Navigate to Dashboard → Calendar
  - [ ] Select all test appointments
  - [ ] Click "Bulk Cancel"
  - [ ] Verify: Test appointments removed
  - **Owner**: QA
  - **Acceptance**: Cleanup successful

### 📊 **5. Monitoring & Observability** (ETA: 1 day)

- [ ] **Sentry Error Tracking**
  - [ ] Verify errors are logged to Sentry
  - [ ] Set up alerts for critical errors
  - [ ] Configure Slack/email notifications
  - **Owner**: Engineering
  - **Acceptance**: Test error triggers alert

- [ ] **Log Aggregation**
  - [ ] Configure log rotation: `docker compose logs` → file
  - [ ] Set up log retention policy (30 days)
  - [ ] Optional: ELK stack or CloudWatch
  - **Owner**: DevOps
  - **Acceptance**: Logs persisted and searchable

- [ ] **Health Check Monitoring**
  - [ ] Set up uptime monitoring (UptimeRobot, Pingdom)
  - [ ] Monitor `/health/live` every 5 minutes
  - [ ] Configure alerts for downtime
  - **Owner**: DevOps
  - **Acceptance**: Alert received when API down

- [ ] **Database Backup**
  - [ ] Test backup script: `./scripts/backup-db.sh`
  - [ ] Schedule daily backups (cron)
  - [ ] Store backups off-site (S3, BackBlaze)
  - [ ] Test restore procedure
  - **Owner**: DevOps
  - **Acceptance**: Backup + restore verified

### 📖 **6. Documentation & Support** (ETA: 1 day)

- [ ] **User Documentation**
  - [ ] Write onboarding guide for new businesses
  - [ ] Document phone number setup
  - [ ] Create FAQ page
  - **Owner**: Product
  - **Acceptance**: Docs published

- [ ] **Admin Documentation**
  - [ ] Document deployment procedure
  - [ ] Create runbook for common issues
  - [ ] Document rollback procedure
  - **Owner**: DevOps
  - **Acceptance**: Runbook complete

- [ ] **Support Channels**
  - [ ] Set up support email (support@yourdomain.com)
  - [ ] Create support ticket system (optional)
  - [ ] Define SLAs for support response
  - **Owner**: Product/Support
  - **Acceptance**: Support channel active

---

## 🚀 LAUNCH DAY

### **Day -1 (Final Prep)**

- [ ] **Final Security Audit**
  - [ ] Review all environment variables
  - [ ] Verify no secrets in git history
  - [ ] Test rate limiting on production
  - **Owner**: Security/Engineering

- [ ] **Performance Test**
  - [ ] Load test with 100 concurrent users
  - [ ] Verify response times < 2 seconds
  - [ ] Check database connection pool usage
  - **Owner**: Engineering

- [ ] **Smoke Test Production**
  - [ ] Run full P0 QA suite on production
  - [ ] Verify all integrations working
  - **Owner**: QA/Engineering

### **Day 0 (Launch)**

- [ ] **09:00 AM - Go Live**
  - [ ] Enable production environment
  - [ ] Monitor error rates in Sentry
  - [ ] Watch server metrics (CPU, memory)

- [ ] **All Day - Active Monitoring**
  - [ ] Monitor Slack/support channels
  - [ ] Track key metrics: signups, bookings, errors
  - [ ] Be ready for hotfixes

- [ ] **End of Day - Retrospective**
  - [ ] Document issues encountered
  - [ ] Plan improvements for Week 1

---

## 📅 POST-LAUNCH (Week 1)

- [ ] **Day 1-3: Stabilization**
  - [ ] Fix critical bugs discovered in production
  - [ ] Monitor error rates daily
  - [ ] Gather user feedback

- [ ] **Day 4-5: Quick Wins**
  - [ ] Implement top user-requested features
  - [ ] Optimize slow API endpoints
  - [ ] Improve error messages

- [ ] **Day 6-7: Planning**
  - [ ] Review week 1 metrics
  - [ ] Plan sprint for Week 2
  - [ ] Prioritize feature backlog

---

## 📋 LAUNCH METRICS TO TRACK

| Metric | Target | Monitor |
|--------|--------|---------|
| Uptime | > 99.9% | UptimeRobot |
| Error Rate | < 0.1% | Sentry |
| API Response Time (p95) | < 1s | Application logs |
| Daily Active Businesses | Growing | Database query |
| Successful Bookings | > 90% | Business logic |
| Support Tickets | < 5/day | Support system |

---

## ⚠️ ROLLBACK PLAN

If critical issues occur:

1. **Immediate**: Switch traffic to maintenance page
2. **Investigate**: Check Sentry, logs, database
3. **Rollback**:
   ```bash
   git checkout <previous-stable-commit>
   ./scripts/prod-up.sh --all
   ```
4. **Communicate**: Notify users via status page
5. **Post-mortem**: Document issue + prevention

---

## ✅ SIGN-OFF

- [ ] **Engineering Lead**: _______________ Date: ___________
- [ ] **Product Lead**: _______________ Date: ___________
- [ ] **QA Lead**: _______________ Date: ___________
- [ ] **DevOps Lead**: _______________ Date: ___________

**Production Ready**: ☐ YES  ☐ NO  ☐ WITH RESERVATIONS

**Notes**:
_________________________________________________________________
_________________________________________________________________


