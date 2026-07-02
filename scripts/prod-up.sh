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
if [ "${1:-}" = "--bundled-db" ]; then
  PROFILES+=(--profile bundled-db)
fi

docker compose -f docker-compose.prod.yml "${PROFILES[@]}" up -d --build

echo ""
echo "Production stack starting. Check status:"
echo "  docker compose -f docker-compose.prod.yml ps"
echo "  docker compose -f docker-compose.prod.yml logs -f api caddy"
echo ""
echo "Health (after DNS points to this server):"
echo "  curl -s https://\${API_DOMAIN}/health/ready"
