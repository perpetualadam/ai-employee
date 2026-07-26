"""Provider tracking on businesses and call logs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "011_provider_tracking"
down_revision: str | None = "010_telecom_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("provider_config", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "call_logs",
        sa.Column("provider", sa.String(32), nullable=True),
    )
    op.create_index("ix_call_logs_provider", "call_logs", ["provider"])

    # Backfill call provider from active phone numbers where possible
    op.execute(
        """
        UPDATE call_logs cl
        SET provider = pn.provider
        FROM phone_numbers pn
        WHERE pn.business_id = cl.business_id
          AND pn.status = 'active'
          AND cl.provider IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_call_logs_provider", table_name="call_logs")
    op.drop_column("call_logs", "provider")
    op.drop_column("businesses", "provider_config")
