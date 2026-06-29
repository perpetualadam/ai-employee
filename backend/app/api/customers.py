"""Customer CRM endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    search: str | None = Query(default=None, max_length=100),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> list:
    return CustomerService.list_customers(db, business.id, search)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    try:
        return CustomerService.create_customer(db, business.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    customer = CustomerService.get_customer(db, business.id, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    customer = CustomerService.get_customer(db, business.id, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    try:
        return CustomerService.update_customer(db, customer, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> None:
    customer = CustomerService.get_customer(db, business.id, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    CustomerService.delete_customer(db, customer)
