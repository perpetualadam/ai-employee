#!/usr/bin/env bash
# Backup PostgreSQL to ./backups/ (dev compose or bundled-db prod).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BACKUP_DIR="${ROOT}/backups"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="${BACKUP_DIR}/aiemployee_${STAMP}.sql.gz"

if docker compose ps db --status running 2>/dev/null | grep -q db; then
  PG_USER="${POSTGRES_USER:-aiemployee}"
  PG_DB="${POSTGRES_DB:-aiemployee}"
  docker compose exec -T db pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$FILE"
elif docker compose -f docker-compose.prod.yml ps db --status running 2>/dev/null | grep -q db; then
  PG_USER="${POSTGRES_USER:-aiemployee}"
  PG_DB="${POSTGRES_DB:-aiemployee}"
  docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$FILE"
elif [ -n "${DATABASE_URL:-}" ]; then
  pg_dump "$DATABASE_URL" | gzip > "$FILE"
else
  echo "No running db container and DATABASE_URL not set."
  exit 1
fi

echo "Backup written: $FILE"
