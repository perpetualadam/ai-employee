"""GDPR-style data export and account deletion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth_cookies import clear_auth_cookie
from app.core.deps import get_current_user, get_user_primary_business
from app.core.rate_limit import limiter
from app.database import get_db
from app.models import Business, User
from app.schemas import AccountDeleteRequest
from app.services.audit_service import AuditService
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get("/export")
@limiter.limit("3/hour")
def export_account_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> dict:
    payload = ComplianceService.export_account_data(db, current_user, business)
    AuditService.log_event(
        db,
        action="data.export",
        resource="account",
        user_id=current_user.id,
        business_id=business.id,
        ip_address=_client_ip(request),
        metadata={"record_counts": {key: len(payload[key]) if isinstance(payload.get(key), list) else 1 for key in ("customers", "jobs", "appointments", "call_logs", "sms_logs")}},
    )
    return payload


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("1/day")
def delete_account(
    request: Request,
    data: AccountDeleteRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> None:
    if data.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Confirmation must be exactly "DELETE".',
        )

    AuditService.log_event(
        db,
        action="account.delete",
        resource="account",
        user_id=current_user.id,
        business_id=business.id,
        ip_address=_client_ip(request),
        metadata={"email": current_user.email},
    )
    ComplianceService.delete_account(db, current_user)
    clear_auth_cookie(response)
