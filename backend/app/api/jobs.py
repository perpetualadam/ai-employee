"""Job/work order endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.models.enums import JobStatus
from app.schemas import JobCreate, JobResponse, JobUpdate
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    status: JobStatus | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> list:
    return JobService.list_jobs(db, business.id, status, customer_id)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    try:
        return JobService.create_job(db, business.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    job = JobService.get_job(db, business.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: str,
    data: JobUpdate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    job = JobService.get_job(db, business.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    try:
        return JobService.update_job(db, job, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> None:
    job = JobService.get_job(db, business.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    JobService.delete_job(db, job)
