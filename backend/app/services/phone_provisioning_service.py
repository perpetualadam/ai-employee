"""Per-tenant phone number search and provisioning via Telnyx."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.phone import is_plausible_phone, normalize_phone
from app.models import Business
from app.voice import telnyx_client

logger = logging.getLogger(__name__)


class PhoneProvisioningService:
    @staticmethod
    def status(business: Business) -> dict:
        configured = telnyx_client.is_phone_provisioning_configured()
        already_provisioned = bool(business.phone_provisioned)
        return {
            "phone_number": business.phone_number,
            "provisioned": already_provisioned,
            "platform_configured": configured,
            # A business that already has a provisioned number cannot provision
            # another one (provision() raises 409), so showing the search form
            # would be misleading.
            "can_search": configured and not already_provisioned,
            "manual_fallback_allowed": not already_provisioned,
            "country": business.country,
        }

    @staticmethod
    def search_available(
        business: Business,
        *,
        prefix: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if not telnyx_client.is_phone_provisioning_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Phone provisioning is not configured on this platform.",
            )
        return telnyx_client.search_available_phone_numbers(
            business.country,
            prefix=prefix,
            limit=limit,
        )

    @staticmethod
    def _assert_number_available(
        db: Session,
        phone_number: str,
        business_id: str,
        country: str,
    ) -> None:
        normalized = normalize_phone(phone_number, country)
        existing = (
            db.query(Business)
            .filter(Business.phone_number.isnot(None), Business.id != business_id)
            .all()
        )
        for other in existing:
            if other.phone_number and normalize_phone(other.phone_number, country) == normalized:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That phone number is already assigned to another business.",
                )

    @staticmethod
    def provision(db: Session, business: Business, phone_number: str) -> dict:
        if business.phone_provisioned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This business already has a provisioned phone number.",
            )
        if not telnyx_client.is_phone_provisioning_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Phone provisioning is not configured on this platform.",
            )

        normalized = normalize_phone(phone_number.strip(), business.country)
        if not is_plausible_phone(normalized, business.country):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid phone number in E.164 format.",
            )

        PhoneProvisioningService._assert_number_available(db, normalized, business.id, business.country)

        settings = get_settings()
        try:
            order = telnyx_client.create_number_order(normalized)
            order_id = order.get("id")
            if order_id:
                telnyx_client.wait_for_number_order(order_id)

            record = telnyx_client.find_phone_number_record(normalized)
            if record is None:
                raise RuntimeError("Purchased number not found in Telnyx account")

            phone_id = record.get("id")
            if not phone_id:
                raise RuntimeError("Telnyx phone number record missing id")

            telnyx_client.configure_phone_number(
                phone_id,
                connection_id=settings.telnyx_texml_connection_id,
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Phone provisioning failed",
                extra={"business_id": business.id, "phone_number": normalized},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not provision phone number: {exc}",
            ) from exc

        business.phone_number = normalized
        business.telnyx_phone_number_id = str(phone_id)
        db.commit()
        db.refresh(business)

        logger.info(
            "Phone number provisioned",
            extra={
                "business_id": business.id,
                "phone_number": normalized,
                "telnyx_phone_number_id": phone_id,
            },
        )
        return {
            "phone_number": normalized,
            "provisioned": True,
            "telnyx_phone_number_id": str(phone_id),
            "message": (
                "Your business phone number is live. Customers can call it now — "
                "inbound calls route to your AI receptionist automatically."
            ),
        }

    @staticmethod
    def save_manual_phone(db: Session, business: Business, phone_number: str) -> Business:
        """Fallback when platform provisioning is unavailable."""
        if business.phone_provisioned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provisioned numbers cannot be edited manually. Contact support.",
            )

        normalized = normalize_phone(phone_number.strip(), business.country)
        if not is_plausible_phone(normalized, business.country):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid phone number in E.164 format.",
            )

        PhoneProvisioningService._assert_number_available(db, normalized, business.id, business.country)
        business.phone_number = normalized
        db.commit()
        db.refresh(business)
        return business
