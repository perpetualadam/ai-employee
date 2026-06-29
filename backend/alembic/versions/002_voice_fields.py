"""Migration 002 — voice call state and escalation phone."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_voice_fields"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("escalation_phone", sa.String(32), nullable=True))
    op.add_column(
        "call_logs",
        sa.Column(
            "conversation_history",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("call_logs", "conversation_history")
    op.drop_column("businesses", "escalation_phone")
