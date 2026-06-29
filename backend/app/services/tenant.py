"""Shared tenant-scoped database helpers."""

from sqlalchemy.orm import Session

from app.models import Customer


def get_customer_for_business(db: Session, business_id: str, customer_id: str) -> Customer | None:
    return (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .first()
    )
