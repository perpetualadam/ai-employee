"""Migration 004 — onboarding completion flag."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_onboarding"
down_revision: Union[str, None] = "003_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("businesses", "onboarding_completed")
