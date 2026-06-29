"""Initial schema — multi-tenant AI employee platform."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    industry = postgresql.ENUM(
        "plumbing", "electrical", "hvac", "roofing", "general",
        name="industry", create_type=False,
    )
    job_status = postgresql.ENUM(
        "lead", "quoted", "scheduled", "in_progress", "completed", "cancelled",
        name="job_status", create_type=False,
    )
    appointment_status = postgresql.ENUM(
        "scheduled", "confirmed", "cancelled", "completed", "no_show",
        name="appointment_status", create_type=False,
    )
    call_direction = postgresql.ENUM("inbound", "outbound", name="call_direction", create_type=False)
    call_status = postgresql.ENUM(
        "ringing", "in_progress", "completed", "missed", "failed", "transferred",
        name="call_status", create_type=False,
    )
    emergency_action = postgresql.ENUM(
        "escalate", "priority_book", "message_owner",
        name="emergency_action", create_type=False,
    )

    for enum_type in (industry, job_status, appointment_status, call_direction, call_status, emergency_action):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "businesses",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("owner_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", industry, nullable=False, server_default="plumbing"),
        sa.Column("country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/New_York"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("working_hours", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ai_instructions", sa.Text(), nullable=True),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_businesses_owner_id", "businesses", ["owner_id"])

    op.create_table(
        "business_services",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_services_business_id", "business_services", ["business_id"])

    op.create_table(
        "business_emergency_rules",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("action", emergency_action, nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_emergency_rules_business_id", "business_emergency_rules", ["business_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "phone", name="uq_customers_business_phone"),
    )
    op.create_index("ix_customers_business_id", "customers", ["business_id"])
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.create_table(
        "call_logs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("customer_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("external_call_id", sa.String(128), nullable=True),
        sa.Column("direction", call_direction, nullable=False),
        sa.Column("status", call_status, nullable=False, server_default="ringing"),
        sa.Column("caller_phone", sa.String(32), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_logs_business_id", "call_logs", ["business_id"])
    op.create_index("ix_call_logs_customer_id", "call_logs", ["customer_id"])
    op.create_index("ix_call_logs_external_call_id", "call_logs", ["external_call_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("customer_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("service_type", sa.String(255), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmation_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_business_id", "appointments", ["business_id"])
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"])
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("customer_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("appointment_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("service_type", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", job_status, nullable=False, server_default="lead"),
        sa.Column("appointment_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_business_id", "jobs", ["business_id"])
    op.create_index("ix_jobs_customer_id", "jobs", ["customer_id"])
    op.create_index("ix_jobs_appointment_id", "jobs", ["appointment_id"])

    op.create_table(
        "ai_activity_logs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("business_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("call_log_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=True),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["call_log_id"], ["call_logs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_activity_logs_business_id", "ai_activity_logs", ["business_id"])
    op.create_index("ix_ai_activity_logs_call_log_id", "ai_activity_logs", ["call_log_id"])


def downgrade() -> None:
    op.drop_table("ai_activity_logs")
    op.drop_table("jobs")
    op.drop_table("appointments")
    op.drop_table("call_logs")
    op.drop_table("customers")
    op.drop_table("business_emergency_rules")
    op.drop_table("business_services")
    op.drop_table("businesses")
    op.drop_table("users")

    for enum_name in (
        "emergency_action", "call_status", "call_direction",
        "appointment_status", "job_status", "industry",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
