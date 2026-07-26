"""Specification: migration 013 creates audit_logs for compliance audit trail."""

from __future__ import annotations

import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models import AuditLog


class Migration013Specification(unittest.TestCase):
    def test_revision_chain_includes_audit_logs_migration(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        config = Config(str(backend_root / "alembic.ini"))
        script = ScriptDirectory.from_config(config)
        revisions = {rev.revision: rev for rev in script.walk_revisions()}

        self.assertIn("013_audit_logs", revisions)
        self.assertEqual(
            revisions["013_audit_logs"].down_revision,
            "012_sms_provider_tracking",
        )

    def test_audit_log_model_targets_audit_logs_table(self) -> None:
        self.assertEqual(AuditLog.__tablename__, "audit_logs")
        column_names = {column.name for column in AuditLog.__table__.columns}
        self.assertIn("action", column_names)
        self.assertIn("resource", column_names)
        self.assertIn("metadata", column_names)

    def test_apply_migrations_requires_audit_logs_table(self) -> None:
        from scripts.apply_migrations import REQUIRED_TABLES

        self.assertIn("audit_logs", REQUIRED_TABLES)


if __name__ == "__main__":
    unittest.main()
