"""Customer CRM service — all queries scoped by business_id."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer
from app.schemas import CustomerCreate, CustomerUpdate

logger = logging.getLogger(__name__)


class CustomerService:
    @staticmethod
    def list_customers(db: Session, business_id: str, search: str | None = None) -> list[Customer]:
        query = db.query(Customer).filter(Customer.business_id == business_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (Customer.name.ilike(term))
                | (Customer.phone.ilike(term))
                | (Customer.email.ilike(term))
            )
        return query.order_by(Customer.created_at.desc()).all()

    @staticmethod
    def list_customers_paginated(
        db: Session,
        business_id: str,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Customer], int]:
        """Return paginated customers and total count."""
        query = db.query(Customer).filter(Customer.business_id == business_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (Customer.name.ilike(term))
                | (Customer.phone.ilike(term))
                | (Customer.email.ilike(term))
            )
        total = query.count()
        customers = query.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()
        return customers, total

    @staticmethod
    def get_customer(db: Session, business_id: str, customer_id: str) -> Customer | None:
        return (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.business_id == business_id)
            .first()
        )

    @staticmethod
    def create_customer(db: Session, business_id: str, data: CustomerCreate) -> Customer:
        customer = Customer(
            business_id=business_id,
            name=data.name.strip(),
            phone=data.phone.strip(),
            email=data.email,
            address=data.address,
            notes=data.notes,
        )
        db.add(customer)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A customer with this phone number already exists") from exc
        db.refresh(customer)
        logger.info("Customer created", extra={"business_id": business_id, "customer_id": customer.id})
        return customer

    @staticmethod
    def update_customer(
        db: Session, customer: Customer, data: CustomerUpdate
    ) -> Customer:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(customer, field, value)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A customer with this phone number already exists") from exc
        db.refresh(customer)
        return customer

    @staticmethod
    def delete_customer(db: Session, customer: Customer) -> None:
        db.delete(customer)
        db.commit()
        logger.info(
            "Customer deleted",
            extra={"business_id": customer.business_id, "customer_id": customer.id},
        )

    @staticmethod
    def lookup_by_phone(db: Session, business_id: str, phone: str) -> Customer | None:
        return (
            db.query(Customer)
            .filter(Customer.business_id == business_id, Customer.phone == phone.strip())
            .first()
        )
