"""Apply Alembic migrations and verify required tables exist."""

from __future__ import annotations

import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings

REQUIRED_TABLES = ("sms_logs", "audit_logs")


def _alembic_config() -> Config:
    cfg = Config("alembic.ini")
    settings = get_settings()
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def apply_migrations() -> None:
    command.upgrade(_alembic_config(), "head")


def verify_required_tables() -> list[str]:
    """Return table names that are still missing after migration."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    return [name for name in REQUIRED_TABLES if name not in existing]


def main() -> int:
    try:
        engine = create_engine(get_settings().database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"Database unavailable: {exc}", file=sys.stderr)
        return 1

    apply_migrations()
    missing = verify_required_tables()
    if missing:
        print(f"Missing tables after migration: {', '.join(missing)}", file=sys.stderr)
        return 1

    print("Migrations applied — required tables present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
