"""Shared tenant-scoped database helpers."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Customer


def is_valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_customer_for_business(db: Session, business_id: str, customer_id: str) -> Customer | None:
    if not is_valid_uuid(customer_id):
        return None
    return (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .first()
    )
