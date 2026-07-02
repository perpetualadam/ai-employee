"""Add trade industry enum values for multi-trade templates."""

from alembic import op

revision: str = "009_trade_industries"
down_revision: str | None = "008_p4_reminders"
branch_labels = None
depends_on = None

_NEW_INDUSTRIES = (
    "gas_engineer",
    "mobile_mechanic",
    "plasterer",
    "carpenter",
    "locksmith",
    "pest_control",
    "landscaping",
    "painter",
    "appliance_repair",
)


def upgrade() -> None:
    for value in _NEW_INDUSTRIES:
        op.execute(f"ALTER TYPE industry ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
