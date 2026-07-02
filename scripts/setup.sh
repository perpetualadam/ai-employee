#!/usr/bin/env bash
# First-time setup for macOS / Linux local development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop (macOS) or Docker Engine (Linux)."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose)."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit with your API keys."
else
  echo ".env already exists — skipped."
fi

docker compose pull db 2>/dev/null || true
docker compose build api
docker compose up -d db api

echo "Waiting for API..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8000/health/live >/dev/null 2>&1; then
    echo "API ready: http://localhost:8000"
    break
  fi
  sleep 2
done

if command -v node >/dev/null 2>&1; then
  echo ""
  echo "Frontend (optional):"
  echo "  cd frontend && npm install && npm run dev"
  echo "  App: http://localhost:3000"
else
  echo ""
  echo "Node.js not found — install Node 20+ for the frontend dev server."
fi

echo ""
echo "Run tests: make test"
