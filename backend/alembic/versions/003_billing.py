"""Migration 003 — Stripe billing fields on businesses."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_billing"
down_revision: Union[str, None] = "002_voice_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    subscription_status = sa.Enum(
        "none", "trialing", "active", "past_due", "canceled", "unpaid",
        name="subscription_status", create_type=False,
    )
    plan_tier = sa.Enum("starter", "pro", name="plan_tier", create_type=False)

    subscription_status.create(op.get_bind(), checkfirst=True)
    plan_tier.create(op.get_bind(), checkfirst=True)

    op.add_column("businesses", sa.Column("stripe_customer_id", sa.String(128), nullable=True))
    op.add_column("businesses", sa.Column("stripe_subscription_id", sa.String(128), nullable=True))
    op.add_column(
        "businesses",
        sa.Column(
            "subscription_status",
            subscription_status,
            nullable=False,
            server_default="trialing",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column("plan_tier", plan_tier, nullable=False, server_default="starter"),
    )
    op.add_column(
        "businesses", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "businesses",
        sa.Column("subscription_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_businesses_stripe_customer_id", "businesses", ["stripe_customer_id"])
    op.create_index("ix_businesses_stripe_subscription_id", "businesses", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_businesses_stripe_subscription_id", "businesses")
    op.drop_index("ix_businesses_stripe_customer_id", "businesses")
    op.drop_column("businesses", "subscription_period_end")
    op.drop_column("businesses", "trial_ends_at")
    op.drop_column("businesses", "plan_tier")
    op.drop_column("businesses", "subscription_status")
    op.drop_column("businesses", "stripe_subscription_id")
    op.drop_column("businesses", "stripe_customer_id")
    sa.Enum(name="plan_tier").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscription_status").drop(op.get_bind(), checkfirst=True)
