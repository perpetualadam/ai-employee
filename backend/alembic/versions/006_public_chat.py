"""Migration 006 — public chat slug and web continuation tokens."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision: str = "006_public_chat"
down_revision: Union[str, None] = "005_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    business_cols = {col["name"] for col in inspector.get_columns("businesses")}

    if "public_slug" not in business_cols:
        op.add_column(
            "businesses",
            sa.Column("public_slug", sa.String(64), nullable=True),
        )
        op.create_index("ix_businesses_public_slug", "businesses", ["public_slug"], unique=True)

    if "web_continuation_tokens" not in inspector.get_table_names():
        op.create_table(
            "web_continuation_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column(
                "business_id",
                postgresql.UUID(as_uuid=False),
                sa.ForeignKey("businesses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "call_log_id",
                postgresql.UUID(as_uuid=False),
                sa.ForeignKey("call_logs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
            sa.UniqueConstraint("token", name="uq_web_continuation_tokens_token"),
        )
        op.create_index(
            "ix_web_continuation_tokens_business_id",
            "web_continuation_tokens",
            ["business_id"],
        )
        op.create_index(
            "ix_web_continuation_tokens_call_log_id",
            "web_continuation_tokens",
            ["call_log_id"],
        )
        op.create_index(
            "ix_web_continuation_tokens_token",
            "web_continuation_tokens",
            ["token"],
        )


def downgrade() -> None:
    op.drop_table("web_continuation_tokens")
    op.drop_index("ix_businesses_public_slug", table_name="businesses")
    op.drop_column("businesses", "public_slug")
