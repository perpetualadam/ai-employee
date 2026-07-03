"""Calendar and appointment endpoints."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.models.enums import AppointmentStatus
from app.schemas import (
    AppointmentBulkCancelRequest,
    AppointmentBulkCancelResponse,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AvailabilityResponse,
    AvailabilitySlot,
)
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> list:
    return AppointmentService.list_appointments(db, business.id, start, end, status_filter)


@router.get("/availability", response_model=AvailabilityResponse)
def check_availability(
    target_date: date = Query(..., alias="date"),
    duration_minutes: int = Query(default=60, ge=15, le=480),
    exclude_appointment_id: str | None = Query(default=None),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    slots = AppointmentService.get_availability(
        db, business, target_date, duration_minutes, exclude_appointment_id
    )
    return AvailabilityResponse(
        date=target_date,
        duration_minutes=duration_minutes,
        slots=[AvailabilitySlot(**slot) for slot in slots],
    )


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: AppointmentCreate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    try:
        return AppointmentService.create_appointment(db, business, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/bulk-cancel", response_model=AppointmentBulkCancelResponse)
def bulk_cancel_appointments(
    data: AppointmentBulkCancelRequest,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> AppointmentBulkCancelResponse:
    """Cancel multiple appointments (e.g. clear test bookings from the calendar)."""
    result = AppointmentService.bulk_cancel_appointments(
        db, business.id, data.appointment_ids
    )
    return AppointmentBulkCancelResponse(**result)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    appointment = AppointmentService.get_appointment(db, business.id, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    appointment = AppointmentService.get_appointment(db, business.id, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    try:
        return AppointmentService.update_appointment(db, business, appointment, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    appointment = AppointmentService.get_appointment(db, business.id, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    try:
        return AppointmentService.cancel_appointment(db, business.id, appointment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
