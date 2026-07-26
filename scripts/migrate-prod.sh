#!/usr/bin/env bash
# Apply Alembic migrations on production (one-shot).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.production.example to .env and fill in values."
  exit 1
fi

PROFILES=()
MODE="${1:-}"

if [ "$MODE" = "--all" ] || [ "$MODE" = "--bundled-db" ]; then
  PROFILES+=(--profile bundled-db)
fi

echo "Applying database migrations (alembic upgrade head)..."
docker compose -f docker-compose.prod.yml "${PROFILES[@]}" run --rm migrate
echo "Migrations complete."
