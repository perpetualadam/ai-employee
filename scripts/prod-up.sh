#!/usr/bin/env bash
# Start production stack on a VPS (macOS/Linux with Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.production.example to .env and fill in values."
  exit 1
fi

PROFILES=(--profile scheduler)
MODE="${1:-}"

if [ "$MODE" = "--all" ] || [ "$MODE" = "--bundled-db" ]; then
  PROFILES+=(--profile bundled-db)
  echo "Starting full stack: app + API + Postgres + scheduler on this VPS."
elif [ -n "$MODE" ]; then
  echo "Unknown option: $MODE"
  echo "Usage: $0 [--all]"
  echo "  --all   Include Postgres on this VPS (everything on one server)"
  exit 1
else
  echo "Starting app + API + scheduler (external DATABASE_URL required)."
fi

echo "Step 1/2 — database migrations (includes audit_logs and other schema updates)..."
docker compose -f docker-compose.prod.yml "${PROFILES[@]}" run --rm migrate

echo "Step 2/2 — starting services..."
docker compose -f docker-compose.prod.yml "${PROFILES[@]}" up -d --build

echo ""
echo "Production stack started. Migrations run automatically on every deploy."
echo "Check status:"
echo "  docker compose -f docker-compose.prod.yml ps"
echo "  docker compose -f docker-compose.prod.yml logs -f api frontend caddy"
echo ""
echo "After DNS points both domains to this server:"
echo "  App:  https://\${APP_DOMAIN}"
echo "  API:  curl -s https://\${API_DOMAIN}/health/ready"
