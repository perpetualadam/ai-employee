"""Telecom regulatory and phone number models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    DocumentType,
    DocumentVerificationStatus,
    PhoneNumberStatus,
    RegulatoryStatus,
)

if TYPE_CHECKING:
    from app.models import Business


def _enum_values(enum_class) -> list[str]:
    return [member.value for member in enum_class]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CountryRegulation(Base):
    """Data-driven country telecom rules — seeded, not hardcoded in services."""

    __tablename__ = "country_regulations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    country_code: Mapped[str] = mapped_column(String(2), unique=True, index=True, nullable=False)
    country_name: Mapped[str] = mapped_column(String(128), nullable=False)
    requires_end_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_regulatory_bundle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_voice: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_sms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_local_numbers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_mobile_numbers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_toll_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class BusinessRegulatoryProfile(Base, TimestampMixin):
    """Per-business regulatory verification state for a country."""

    __tablename__ = "business_regulatory_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    status: Mapped[RegulatoryStatus] = mapped_column(
        Enum(RegulatoryStatus, name="regulatory_status", values_callable=_enum_values),
        default=RegulatoryStatus.PENDING,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_end_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_bundle_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business"] = relationship("Business", back_populates="regulatory_profiles")
    documents: Mapped[list["UploadedDocument"]] = relationship(
        "UploadedDocument", back_populates="regulatory_profile", cascade="all, delete-orphan"
    )


class UploadedDocument(Base, TimestampMixin):
    """Regulatory document metadata — file bytes live in object storage."""

    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regulatory_profile_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("business_regulatory_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", values_callable=_enum_values),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    provider_document_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verification_status: Mapped[DocumentVerificationStatus] = mapped_column(
        Enum(DocumentVerificationStatus, name="document_verification_status", values_callable=_enum_values),
        default=DocumentVerificationStatus.PENDING,
        nullable=False,
    )

    regulatory_profile: Mapped[Optional["BusinessRegulatoryProfile"]] = relationship(
        "BusinessRegulatoryProfile", back_populates="documents"
    )


class PhoneNumber(Base, TimestampMixin):
    """Provider-agnostic phone number inventory per business."""

    __tablename__ = "phone_numbers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_number_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[PhoneNumberStatus] = mapped_column(
        Enum(PhoneNumberStatus, name="phone_number_status", values_callable=_enum_values),
        default=PhoneNumberStatus.PENDING,
        nullable=False,
    )
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business: Mapped["Business"] = relationship("Business", back_populates="phone_numbers")
