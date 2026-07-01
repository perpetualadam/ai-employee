"""Migration 005 — conversation channel, AI summary, address confirmation tokens."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_conversations"
down_revision: Union[str, None] = "004_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

conversation_channel = postgresql.ENUM(
    "voice",
    "sms",
    "web_chat",
    name="conversation_channel",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE conversation_channel AS ENUM ('voice', 'sms', 'web_chat')"
    )
    op.add_column(
        "call_logs",
        sa.Column(
            "channel",
            conversation_channel,
            nullable=False,
            server_default="voice",
        ),
    )
    op.add_column(
        "call_logs",
        sa.Column("parent_call_log_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.add_column(
        "call_logs",
        sa.Column("ai_summary", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_call_logs_parent_call_log_id",
        "call_logs",
        "call_logs",
        ["parent_call_log_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_call_logs_parent_call_log_id",
        "call_logs",
        ["parent_call_log_id"],
    )

    # Text chat sessions: caller_phone is "text-chat" or dashboard preview
    op.execute(
        """
        UPDATE call_logs
        SET channel = 'web_chat'
        WHERE external_call_id IS NULL
          AND (caller_phone IS NULL OR caller_phone IN ('text-chat', 'unknown'))
        """
    )

    op.create_table(
        "address_confirmation_tokens",
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
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_address", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("token", name="uq_address_confirmation_tokens_token"),
    )
    op.create_index(
        "ix_address_confirmation_tokens_business_id",
        "address_confirmation_tokens",
        ["business_id"],
    )
    op.create_index(
        "ix_address_confirmation_tokens_call_log_id",
        "address_confirmation_tokens",
        ["call_log_id"],
    )
    op.create_index(
        "ix_address_confirmation_tokens_token",
        "address_confirmation_tokens",
        ["token"],
    )


def downgrade() -> None:
    op.drop_table("address_confirmation_tokens")
    op.drop_constraint("fk_call_logs_parent_call_log_id", "call_logs", type_="foreignkey")
    op.drop_index("ix_call_logs_parent_call_log_id", table_name="call_logs")
    op.drop_column("call_logs", "ai_summary")
    op.drop_column("call_logs", "parent_call_log_id")
    op.drop_column("call_logs", "channel")
    op.execute("DROP TYPE conversation_channel")
