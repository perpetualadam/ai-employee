"""Specification: migration 012 creates sms_logs for SMS provider tracking."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings
from app.models import SmsLog


def _postgres_available() -> bool:
    try:
        engine = create_engine(get_settings().database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class Migration012Specification(unittest.TestCase):
    def test_revision_chain_includes_sms_logs_migration(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        config = Config(str(backend_root / "alembic.ini"))
        script = ScriptDirectory.from_config(config)
        revisions = {rev.revision: rev for rev in script.walk_revisions()}

        self.assertIn("012_sms_provider_tracking", revisions)
        self.assertEqual(
            revisions["012_sms_provider_tracking"].down_revision,
            "011_provider_tracking",
        )

    def test_sms_log_model_targets_sms_logs_table(self) -> None:
        self.assertEqual(SmsLog.__tablename__, "sms_logs")
        column_names = {column.name for column in SmsLog.__table__.columns}
        self.assertIn("provider", column_names)
        self.assertIn("business_id", column_names)
        self.assertIn("to_number", column_names)
        self.assertIn("sent", column_names)

    def test_migration_module_declares_expected_indexes(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "012_sms_provider_tracking.py"
        )
        source = migration_path.read_text(encoding="utf-8")
        self.assertIn('op.create_table(\n        "sms_logs"', source)
        self.assertIn('sa.Column("provider", sa.String(32), nullable=False)', source)
        self.assertIn('op.create_index("ix_sms_logs_provider", "sms_logs", ["provider"])', source)


@unittest.skipUnless(
    os.environ.get("RUN_DB_MIGRATION_TESTS", "").lower() in ("1", "true", "yes")
    or _postgres_available(),
    "PostgreSQL not available — set RUN_DB_MIGRATION_TESTS=1 with DATABASE_URL",
)
class Migration012IntegrationSpecification(unittest.TestCase):
    def test_apply_migrations_creates_sms_logs_table(self) -> None:
        from scripts.apply_migrations import apply_migrations, verify_required_tables

        apply_migrations()
        missing = verify_required_tables()
        self.assertEqual(missing, [])

        engine = create_engine(get_settings().database_url)
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("sms_logs")}
        self.assertIn("provider", columns)
        self.assertIn("external_id", columns)


if __name__ == "__main__":
    unittest.main()
