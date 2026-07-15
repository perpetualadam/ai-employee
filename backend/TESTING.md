# Testing Guide

Complete testing strategy for AI Employee.

## Test Suites

### 1. **Unit Tests** (116 spec tests)

Located in `backend/tests/` - Fast, isolated tests for business logic.

**Run locally:**
```bash
cd backend
PYTHONPATH=. GROQ_API_KEY=test-dummy python -m unittest discover -s tests -v
```

**Run in Docker:**
```bash
docker compose exec api python -m unittest discover -s tests -v
```

**Coverage:**
- Voice session guards & booking flow
- Text chat receptionist flow
- Intake validation (names, addresses)
- Slot booking precision
- Webhook signature verification
- Multi-trade templates
- Domain layer (pure business logic)

### 2. **Smoke Tests**

Quick health checks for critical functionality.

**Run:**
```bash
python scripts/smoke_test.py
python scripts/smoke_test.py --api-url https://api.yourdomain.com
```

**Tests:**
- Health endpoints (`/health/live`, `/health/ready`, `/health`)
- Authentication (register, login, /me)
- Rate limiting detection
- Database operations (CRUD)
- Pagination

**Exit codes:**
- `0` = All tests passed
- `1` = One or more tests failed

### 3. **Integration Tests**

End-to-end booking flow testing.

**Run:**
```bash
python scripts/integration_test.py
python scripts/integration_test.py --api-url https://api.yourdomain.com
python scripts/integration_test.py --skip-cleanup  # Keep test data
```

**Test flow:**
1. Register user
2. Get user profile
3. Get business profile
4. Update business settings
5. Create customer
6. Check availability
7. Book appointment
8. List appointments
9. Cleanup (cancel appointment)

### 4. **Multi-Trade QA (P0)**

Automated tests for different trade types.

**Run all trades:**
```bash
PYTHONPATH=. python scripts/p0_trade_qa.py
```

**Run specific trades:**
```bash
PYTHONPATH=. python scripts/p0_trade_qa.py plumbing gas_engineer mobile_mechanic
```

**Tests per trade:**
- Onboarding data seeding
- Service templates
- Emergency rules
- Address hints (country-specific)
- Compliance blocks

### 5. **Complete Test Suite**

Run all tests in sequence:

**Bash (Linux/macOS):**
```bash
./scripts/run_all_tests.sh
./scripts/run_all_tests.sh --api-url https://api.yourdomain.com
./scripts/run_all_tests.sh --skip-unit  # Skip unit tests
```

**Windows (PowerShell):**
```powershell
# Run each test suite manually
cd backend
python -m unittest discover -s tests -v
python scripts/smoke_test.py
python scripts/integration_test.py
python scripts/p0_trade_qa.py
```

## Manual Testing (P0 QA Checklist)

See `P0_QA.md` for manual test procedures:

1. **Text chat booking** - 3 trades (plumbing US, gas engineer GB, mobile mechanic US)
2. **Voice call booking** - Live Telnyx call
3. **SMS confirmations** - Verify delivery
4. **Email confirmations** - Verify delivery

## CI/CD Testing

GitHub Actions runs automatically on push to `main`:

```yaml
# .github/workflows/ci.yml
- Backend spec tests (116 tests)
- Frontend lint + build
```

**View results:** https://github.com/perpetualadam/ai-employee/actions

## Pre-Deployment Testing

**Before every production deploy:**

```bash
# 1. Run full test suite
./scripts/run_all_tests.sh --api-url https://staging.yourdomain.com

# 2. Manual P0 QA
# Follow P0_QA.md checklist

# 3. Verify in production-like environment
python scripts/smoke_test.py --api-url https://staging.yourdomain.com
```

## Performance Testing

**Load testing with Apache Bench:**

```bash
# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health/live

# Test authenticated endpoint
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/customers
```

**Expected performance:**
- Health endpoints: < 100ms (p95)
- Authenticated APIs: < 500ms (p95)
- Booking flow: < 2s (p95)

## Debugging Test Failures

### Unit Test Failures

```bash
# Run specific test file
PYTHONPATH=. python -m unittest tests.test_intake_spec -v

# Run specific test
PYTHONPATH=. python -m unittest tests.test_intake_spec.IntakeSpecification.test_accepts_full_street_address -v
```

### Integration Test Failures

Enable verbose logging:

```python
# In integration_test.py, add to __init__:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### API Request Debugging

```bash
# Enable debug mode in .env
DEBUG=true

# Watch logs
docker compose logs -f api

# Or check specific request
curl -v http://localhost:8000/health
```

## Test Data Cleanup

**After manual testing:**

```bash
# Bulk cancel test appointments
# Dashboard → Calendar → Select all → Bulk Cancel

# Or via API:
curl -X POST http://localhost:8000/api/v1/appointments/bulk-cancel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"appointment_ids": ["id1", "id2"]}'
```

## Coverage Report (Future)

Add coverage tracking:

```bash
pip install coverage
coverage run -m unittest discover -s tests
coverage report
coverage html  # Generate HTML report
```

## Testing Best Practices

1. **Run tests before every commit**
2. **Add tests for new features**
3. **Keep tests fast** (< 5 seconds for unit tests)
4. **Use descriptive test names**
5. **Mock external APIs** (Groq, Telnyx, Stripe)
6. **Clean up test data**
7. **Run full suite before deployment**
