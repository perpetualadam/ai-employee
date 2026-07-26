"""012 — SMS provider tracking on sms_logs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "012_sms_provider_tracking"
down_revision: str | None = "011_provider_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sms_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("inbound", "outbound", name="call_direction", create_type=False),
            nullable=False,
            server_default="outbound",
        ),
        sa.Column("from_number", sa.String(32), nullable=True),
        sa.Column("to_number", sa.String(32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sms_logs_business_id", "sms_logs", ["business_id"])
    op.create_index("ix_sms_logs_provider", "sms_logs", ["provider"])
    op.create_index("ix_sms_logs_to_number", "sms_logs", ["to_number"])
    op.create_index("ix_sms_logs_external_id", "sms_logs", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_sms_logs_external_id", table_name="sms_logs")
    op.drop_index("ix_sms_logs_to_number", table_name="sms_logs")
    op.drop_index("ix_sms_logs_provider", table_name="sms_logs")
    op.drop_index("ix_sms_logs_business_id", table_name="sms_logs")
    op.drop_table("sms_logs")
