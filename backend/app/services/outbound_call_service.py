"""Outbound callback calls via TelephonyProvider (CallService)."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.phone import is_plausible_phone, normalize_phone
from app.models import Business, CallLog, Customer
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.providers.exceptions import ProviderError
from app.providers.factory import get_call_service
from app.services.customer_service import CustomerService
from app.utils.errors import http_exception_from_provider
logger = logging.getLogger(__name__)


class OutboundCallService:
    @staticmethod
    def initiate_callback(
        db: Session,
        business: Business,
        *,
        customer_id: str | None = None,
        phone: str | None = None,
        reason: str | None = None,
    ) -> CallLog:
        if not get_call_service(business=business, db=db).is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Outbound calling is not configured on this platform.",
            )

        from_number = business.phone_number
        if not from_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provision a business phone number before placing outbound calls.",
            )

        customer: Customer | None = None
        if customer_id:
            customer = CustomerService.get_customer(db, business.id, customer_id)
            if customer is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
            phone = customer.phone

        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A customer phone number is required.",
            )

        to_number = normalize_phone(phone, business.country)
        if not is_plausible_phone(to_number, business.country):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer phone number is not valid.",
            )

        settings = get_settings()
        call_log = CallLog(
            id=str(uuid4()),
            business_id=business.id,
            customer_id=customer.id if customer else None,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            channel=ConversationChannel.VOICE,
            caller_phone=from_number,
            summary=reason or "Outbound callback to customer",
        )
        db.add(call_log)
        db.commit()
        db.refresh(call_log)

        webhook_url = (
            f"{settings.public_api_url.rstrip('/')}{settings.api_v1_prefix}"
            f"/voice/outbound/answer?call_log_id={call_log.id}"
        )

        try:
            call_service = get_call_service(business=business, db=db)
            result = asyncio.run(
                call_service.place_outbound_call(
                    from_number=from_number,
                    to_number=to_number,
                    webhook_url=webhook_url,
                )
            )
            call_log.external_call_id = result.get("call_id") or result.get("call_control_id")
            call_log.provider = result.get("provider")
            db.commit()
            db.refresh(call_log)
        except ProviderError as exc:
            call_log.status = CallStatus.FAILED
            db.commit()
            logger.exception(
                "Outbound call failed",
                extra={"business_id": business.id, "call_log_id": call_log.id},
            )
            raise http_exception_from_provider(exc) from exc
        except Exception as exc:
            call_log.status = CallStatus.FAILED
            db.commit()
            logger.exception(
                "Outbound call failed",
                extra={"business_id": business.id, "call_log_id": call_log.id},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not place outbound call: {exc}",
            ) from exc

        logger.info(
            "Outbound callback initiated",
            extra={
                "business_id": business.id,
                "call_log_id": call_log.id,
                "to": to_number,
            },
        )
        return call_log
