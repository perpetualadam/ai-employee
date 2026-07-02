#!/usr/bin/env bash
# Start local dev stack (macOS / Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE_ARGS=()
if [ "${1:-}" = "--scheduler" ]; then
  PROFILE_ARGS=(--profile scheduler)
fi

docker compose "${PROFILE_ARGS[@]}" up -d --build
echo "API: http://localhost:8000  |  Docs: http://localhost:8000/docs"
echo "Logs: docker compose logs -f api"
