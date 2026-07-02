#!/usr/bin/env bash
# Restore PostgreSQL from a gzipped pg_dump file.
# Usage: ./scripts/restore-db.sh backups/aiemployee_20260101_120000.sql.gz
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BACKUP="$1"

if [ ! -f "$BACKUP" ]; then
  echo "File not found: $BACKUP"
  exit 1
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "WARNING: This will overwrite the current database."
read -r -p "Type yes to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

if docker compose ps db --status running 2>/dev/null | grep -q db; then
  COMPOSE=(docker compose)
elif docker compose -f docker-compose.prod.yml ps db --status running 2>/dev/null | grep -q db; then
  COMPOSE=(docker compose -f docker-compose.prod.yml)
else
  echo "No running db container. For managed Postgres use: gunzip -c $BACKUP | psql \$DATABASE_URL"
  exit 1
fi

PG_USER="${POSTGRES_USER:-aiemployee}"
PG_DB="${POSTGRES_DB:-aiemployee}"
gunzip -c "$BACKUP" | "${COMPOSE[@]}" exec -T db psql -U "$PG_USER" -d "$PG_DB"
echo "Restore complete."
