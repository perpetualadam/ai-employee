"""Outbound voice call endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_active_subscription
from app.database import get_db
from app.models import Business
from app.schemas import OutboundCallRequest, OutboundCallResponse
from app.services.outbound_call_service import OutboundCallService

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/outbound", response_model=OutboundCallResponse)
def place_outbound_call(
    body: OutboundCallRequest,
    business: Business = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> OutboundCallResponse:
    """Call a customer back from the business line (connects to escalation phone when answered)."""
    call_log = OutboundCallService.initiate_callback(
        db,
        business,
        customer_id=body.customer_id,
        phone=body.phone,
        reason=body.reason,
    )
    return OutboundCallResponse(
        call_log_id=call_log.id,
        status=call_log.status.value,
        external_call_id=call_log.external_call_id,
        message="Outbound call initiated.",
    )
