"""Migration 007 — per-tenant Telnyx phone provisioning metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "007_phone_provisioning"
down_revision: Union[str, None] = "006_public_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    business_cols = {col["name"] for col in inspector.get_columns("businesses")}

    if "telnyx_phone_number_id" not in business_cols:
        op.add_column(
            "businesses",
            sa.Column("telnyx_phone_number_id", sa.String(64), nullable=True),
        )

    indexes = {idx["name"] for idx in inspector.get_indexes("businesses")}
    if "ix_businesses_phone_number" not in indexes:
        op.create_index(
            "ix_businesses_phone_number",
            "businesses",
            ["phone_number"],
            unique=True,
            postgresql_where=sa.text("phone_number IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("ix_businesses_phone_number", table_name="businesses")
    op.drop_column("businesses", "telnyx_phone_number_id")
