"""Migration 014 — call recording retention and inbound SMS audit fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "014_call_sms_recording"
down_revision: Union[str, None] = "013_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    business_cols = {col["name"] for col in inspector.get_columns("businesses")}
    call_cols = {col["name"] for col in inspector.get_columns("call_logs")}
    sms_cols = {col["name"] for col in inspector.get_columns("sms_logs")}

    if "recording_enabled" not in business_cols:
        op.add_column(
            "businesses",
            sa.Column(
                "recording_enabled",
                sa.Boolean(),
                nullable=False,
                server_default="true",
            ),
        )

    if "recording_status" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("recording_status", sa.String(32), nullable=True),
        )
    if "recording_storage_key" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("recording_storage_key", sa.String(512), nullable=True),
        )
    if "recording_content_type" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("recording_content_type", sa.String(64), nullable=True),
        )
    if "recording_duration_seconds" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("recording_duration_seconds", sa.Integer(), nullable=True),
        )
    if "external_recording_id" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("external_recording_id", sa.String(128), nullable=True),
        )
    if "provider_recording_url" not in call_cols:
        op.add_column(
            "call_logs",
            sa.Column("provider_recording_url", sa.Text(), nullable=True),
        )

    if "call_log_id" not in sms_cols:
        op.add_column(
            "sms_logs",
            sa.Column(
                "call_log_id",
                UUID(as_uuid=False),
                sa.ForeignKey("call_logs.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_sms_logs_call_log_id", "sms_logs", ["call_log_id"])
    if "raw_payload" not in sms_cols:
        op.add_column(
            "sms_logs",
            sa.Column("raw_payload", JSONB(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("sms_logs", "raw_payload")
    op.drop_index("ix_sms_logs_call_log_id", table_name="sms_logs")
    op.drop_column("sms_logs", "call_log_id")
    op.drop_column("call_logs", "provider_recording_url")
    op.drop_column("call_logs", "external_recording_id")
    op.drop_column("call_logs", "recording_duration_seconds")
    op.drop_column("call_logs", "recording_content_type")
    op.drop_column("call_logs", "recording_storage_key")
    op.drop_column("call_logs", "recording_status")
    op.drop_column("businesses", "recording_enabled")
