"""Specification: migration 014 adds call recording and inbound SMS audit fields."""

from __future__ import annotations

import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models import Business, CallLog, SmsLog


class Migration014Specification(unittest.TestCase):
    def test_revision_chain_includes_call_sms_recording_migration(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        config = Config(str(backend_root / "alembic.ini"))
        script = ScriptDirectory.from_config(config)
        revisions = {rev.revision: rev for rev in script.walk_revisions()}

        self.assertIn("014_call_sms_recording", revisions)
        self.assertEqual(
            revisions["014_call_sms_recording"].down_revision,
            "013_audit_logs",
        )

    def test_models_include_recording_and_sms_audit_fields(self) -> None:
        business_cols = {column.name for column in Business.__table__.columns}
        call_cols = {column.name for column in CallLog.__table__.columns}
        sms_cols = {column.name for column in SmsLog.__table__.columns}

        self.assertIn("recording_enabled", business_cols)
        self.assertIn("recording_storage_key", call_cols)
        self.assertIn("recording_status", call_cols)
        self.assertIn("call_log_id", sms_cols)
        self.assertIn("raw_payload", sms_cols)


if __name__ == "__main__":
    unittest.main()
