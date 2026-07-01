"""Address confirmation links — SMS recovery when voice STT fails on address."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.intake import is_valid_service_address
from app.domain.phone import is_plausible_phone, normalize_phone
from app.models import AddressConfirmationToken, Business, CallLog, Customer
from app.schemas import CustomerCreate, CustomerUpdate
from app.services.customer_service import CustomerService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 24


class AddressConfirmationService:
    @staticmethod
    def create_and_send_link(
        db: Session,
        business: Business,
        call_log: CallLog,
        *,
        customer_name: str | None = None,
        customer_id: str | None = None,
    ) -> dict:
        settings = get_settings()
        phone = call_log.caller_phone
        if not phone or not is_plausible_phone(normalize_phone(phone)):
            return {"sent": False, "link_created": False, "error": "No valid caller phone for SMS"}

        token_value = secrets.token_urlsafe(32)
        token = AddressConfirmationToken(
            id=str(uuid4()),
            business_id=business.id,
            call_log_id=call_log.id,
            customer_id=customer_id,
            token=token_value,
            customer_name=customer_name,
            expires_at=datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS),
        )
        db.add(token)
        db.commit()

        confirm_url = f"{settings.frontend_url.rstrip('/')}/confirm-address/{token_value}"
        message = (
            f"{business.name}: Please confirm your service address here: {confirm_url}"
        )
        notifications = NotificationService(db, business)
        result = notifications.send_sms(normalize_phone(phone), message)

        logger.info(
            "Address confirmation link created",
            extra={
                "call_log_id": call_log.id,
                "business_id": business.id,
                "sms_sent": result.get("sent"),
                "url": confirm_url,
            },
        )
        return {
            "sent": result.get("sent", False),
            "link_created": True,
            "token_id": token.id,
            "url": confirm_url,
            "sms_error": result.get("error"),
        }

    @staticmethod
    def get_public_token(db: Session, token_value: str) -> AddressConfirmationToken | None:
        token = (
            db.query(AddressConfirmationToken)
            .filter(AddressConfirmationToken.token == token_value)
            .first()
        )
        if token is None:
            return None
        if token.confirmed_at:
            return token
        if token.expires_at < datetime.now(UTC):
            return None
        return token

    @staticmethod
    def confirm_address(
        db: Session,
        token_value: str,
        address: str,
    ) -> tuple[bool, str]:
        token = AddressConfirmationService.get_public_token(db, token_value)
        if token is None:
            return False, "This link is invalid or has expired."

        if token.confirmed_at:
            return True, token.confirmed_address or "Address already confirmed."

        if not is_valid_service_address(address):
            return False, (
                "Please enter a complete US address: house number, street, city, state, and ZIP."
            )

        business = db.query(Business).filter(Business.id == token.business_id).first()
        call = db.query(CallLog).filter(CallLog.id == token.call_log_id).first()
        if business is None or call is None:
            return False, "Session not found."

        customer: Customer | None = None
        if token.customer_id:
            customer = CustomerService.get_customer(db, token.business_id, token.customer_id)

        phone = call.caller_phone
        if customer is None and phone and is_plausible_phone(normalize_phone(phone)):
            customer = CustomerService.lookup_by_phone(db, token.business_id, phone)

        if customer is None:
            name = token.customer_name or "Customer"
            customer = CustomerService.create_customer(
                db,
                token.business_id,
                CustomerCreate(
                    name=name,
                    phone=normalize_phone(phone or ""),
                    address=address.strip(),
                ),
            )
        else:
            customer = CustomerService.update_customer(
                db,
                customer,
                CustomerUpdate(address=address.strip()),
            )

        token.confirmed_at = datetime.now(UTC)
        token.confirmed_address = address.strip()
        token.customer_id = customer.id
        call.customer_id = customer.id

        history = list(call.conversation_history or [])
        history.append(
            {
                "role": "system",
                "content": f"Customer confirmed service address via link: {address.strip()}",
                "channel": "sms",
            }
        )
        call.conversation_history = history
        db.commit()

        logger.info(
            "Address confirmed via link",
            extra={"call_log_id": call.id, "customer_id": customer.id},
        )
        return True, address.strip()
