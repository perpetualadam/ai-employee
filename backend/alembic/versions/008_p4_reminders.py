"""Migration 008 — appointment reminders and business reminder toggle."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "008_p4_reminders"
down_revision: Union[str, None] = "007_phone_provisioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    business_cols = {col["name"] for col in inspector.get_columns("businesses")}
    appt_cols = {col["name"] for col in inspector.get_columns("appointments")}

    if "reminders_enabled" not in business_cols:
        op.add_column(
            "businesses",
            sa.Column("reminders_enabled", sa.Boolean(), nullable=False, server_default="true"),
        )

    if "reminder_sent_at" not in appt_cols:
        op.add_column(
            "appointments",
            sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("appointments", "reminder_sent_at")
    op.drop_column("businesses", "reminders_enabled")
