# Rate Limiting

Rate limiting is enabled to prevent abuse and ensure fair usage across all users.

## Implementation

Using **SlowAPI** with in-memory storage (development) or Redis (production).

## Rate Limits by Endpoint

### Authentication

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `POST /auth/register` | 3/hour per IP | Prevent account spam |
| `POST /auth/login` | 5/minute per IP | Prevent brute force attacks |

### Public Endpoints

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `POST /public/chat/{slug}` | 20/minute per IP | Prevent chat abuse |
| `POST /public/continue/{token}` | 20/minute per IP | Prevent chat abuse |

### Dashboard Receptionist

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `POST /receptionist/chat` | 30/minute per user | AI cost control |

### Global Default

All other endpoints: **1000/hour per IP**

## Production Setup with Redis

For production, use Redis for distributed rate limiting:

1. **Install Redis**:
   ```bash
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

2. **Update configuration** in `app/core/rate_limit.py`:
   ```python
   limiter = Limiter(
       key_func=get_remote_address,
       default_limits=["1000/hour"],
       storage_uri="redis://localhost:6379",  # Update this
   )
   ```

3. **Environment variable option** (add to `app/config.py`):
   ```python
   redis_url: str = "redis://localhost:6379"
   ```

## Error Response

When rate limit is exceeded, API returns HTTP 429:

```json
{
  "error": "rate_limit_exceeded",
  "detail": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

## Testing Rate Limits

```bash
# Test login rate limit (should fail after 5 requests)
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' \
    -w "\nStatus: %{http_code}\n"
  sleep 1
done
```

## Monitoring

Monitor rate limit hits in logs:
```
INFO: Rate limit exceeded for 192.168.1.1 on /auth/login
```

## Bypassing in Development

To disable rate limiting in development, set in `app/core/rate_limit.py`:

```python
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not settings.debug,  # Disable when DEBUG=true
)
```

## Custom Limits per User

Future enhancement: use `business_id` instead of IP for authenticated endpoints:

```python
def get_business_id(request: Request):
    # Extract from JWT token
    return business_id or get_remote_address(request)

limiter = Limiter(key_func=get_business_id)
```
