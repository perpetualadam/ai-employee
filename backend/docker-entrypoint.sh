#!/usr/bin/env sh
# Run Alembic migrations before starting the API (used as container entrypoint).
set -eu

echo "Waiting for database and applying migrations..."
python scripts/apply_migrations.py

echo "Starting: $*"
exec "$@"
