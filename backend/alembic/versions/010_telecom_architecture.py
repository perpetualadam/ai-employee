"""Telecom architecture tables and country regulation seed."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010_telecom_architecture"
down_revision: str | None = "009_trade_industries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "country_regulations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("country_name", sa.String(128), nullable=False),
        sa.Column("requires_end_user", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_regulatory_bundle", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_voice", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supports_sms", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supports_local_numbers", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supports_mobile_numbers", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_toll_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_country_regulations_country_code", "country_regulations", ["country_code"], unique=True)

    regulatory_status = sa.Enum(
        "not_required",
        "pending",
        "documents_required",
        "submitted",
        "approved",
        "rejected",
        name="regulatory_status",
    )
    regulatory_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "business_regulatory_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("status", regulatory_status, nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="telnyx"),
        sa.Column("provider_end_user_id", sa.String(128), nullable=True),
        sa.Column("provider_bundle_id", sa.String(128), nullable=True),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_business_regulatory_profiles_business_id", "business_regulatory_profiles", ["business_id"])
    op.create_index("ix_business_regulatory_profiles_country_code", "business_regulatory_profiles", ["country_code"])

    document_type = sa.Enum(
        "business_registration",
        "proof_of_address",
        "id_document",
        "other",
        name="document_type",
    )
    document_type.create(op.get_bind(), checkfirst=True)

    document_verification_status = sa.Enum(
        "pending",
        "uploaded",
        "submitted",
        "approved",
        "rejected",
        name="document_verification_status",
    )
    document_verification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "uploaded_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("regulatory_profile_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("business_regulatory_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("provider_document_id", sa.String(128), nullable=True),
        sa.Column("verification_status", document_verification_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_uploaded_documents_business_id", "uploaded_documents", ["business_id"])

    phone_number_status = sa.Enum(
        "pending",
        "provisioning",
        "active",
        "failed",
        "released",
        name="phone_number_status",
    )
    phone_number_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "phone_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="telnyx"),
        sa.Column("provider_number_id", sa.String(128), nullable=True),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("status", phone_number_status, nullable=False, server_default="pending"),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_phone_numbers_business_id", "phone_numbers", ["business_id"])
    op.create_index("ix_phone_numbers_phone_number", "phone_numbers", ["phone_number"], unique=True)

    # Seed country regulations
    from app.data.country_regulations_seed import COUNTRY_REGULATION_SEED

    conn = op.get_bind()
    for row in COUNTRY_REGULATION_SEED:
        conn.execute(
            sa.text(
                """
                INSERT INTO country_regulations (
                    id, country_code, country_name,
                    requires_end_user, requires_regulatory_bundle,
                    supports_voice, supports_sms, supports_local_numbers,
                    supports_mobile_numbers, supports_toll_free, metadata
                ) VALUES (
                    gen_random_uuid()::text, :country_code, :country_name,
                    :requires_end_user, :requires_regulatory_bundle,
                    :supports_voice, :supports_sms, :supports_local_numbers,
                    :supports_mobile_numbers, :supports_toll_free, CAST(:metadata AS jsonb)
                )
                ON CONFLICT (country_code) DO NOTHING
                """
            ),
            {
                **row,
                "metadata": __import__("json").dumps(row.get("metadata", {})),
            },
        )


def downgrade() -> None:
    op.drop_table("phone_numbers")
    op.drop_table("uploaded_documents")
    op.drop_table("business_regulatory_profiles")
    op.drop_table("country_regulations")
    sa.Enum(name="phone_number_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="document_verification_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="document_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="regulatory_status").drop(op.get_bind(), checkfirst=True)
