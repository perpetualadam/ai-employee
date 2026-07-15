"""Public endpoints — customer chat and token-based flows (no auth)."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.database import SessionLocal, get_db
from app.models import Business
from app.schemas import (
    AddressConfirmInfoResponse,
    AddressConfirmRequest,
    AddressConfirmResponse,
    PublicChatInfoResponse,
    PublicChatRequest,
    PublicChatResponse,
    PublicContinueInfoResponse,
)
from app.services.address_confirmation_service import AddressConfirmationService
from app.services.conversation_summary_service import ConversationSummaryService
from app.services.public_chat_service import PublicChatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["public"])


async def _summarize_conversation(call_log_id: str) -> None:
    db = SessionLocal()
    try:
        await ConversationSummaryService.maybe_summarize(db, call_log_id)
    finally:
        db.close()


@router.get("/chat/{slug}", response_model=PublicChatInfoResponse)
def get_public_chat_info(slug: str, db: Session = Depends(get_db)) -> PublicChatInfoResponse:
    business = PublicChatService.get_business_for_slug(db, slug)
    return PublicChatInfoResponse(
        business_name=business.name,
        public_slug=business.public_slug or slug,
        phone_number=business.phone_number,
    )


@router.post("/chat/{slug}", response_model=PublicChatResponse)
@limiter.limit("20/minute")
async def public_chat_by_slug(
    request: Request,
    slug: str,
    data: PublicChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PublicChatResponse:
    business = PublicChatService.get_business_for_slug(db, slug)
    result = await PublicChatService.chat(
        db,
        business,
        user_message=data.message,
        history=[h.model_dump() for h in data.history],
        session_id=data.session_id,
        customer_phone=data.customer_phone,
    )
    background_tasks.add_task(_summarize_conversation, result["session_id"])
    return PublicChatResponse(**result)


@router.get("/continue/{token}", response_model=PublicContinueInfoResponse)
def get_continue_chat_info(token: str, db: Session = Depends(get_db)) -> PublicContinueInfoResponse:
    business, call = PublicChatService.get_session_for_continue_token(db, token)
    messages = [
        {"role": entry["role"], "content": entry["content"]}
        for entry in (call.conversation_history or [])
        if entry.get("role") in ("user", "assistant") and entry.get("content")
    ]
    return PublicContinueInfoResponse(
        business_name=business.name,
        session_id=call.id,
        phone_number=business.phone_number,
        messages=messages,
        voice_handoff=True,
    )


@router.post("/continue/{token}", response_model=PublicChatResponse)
@limiter.limit("20/minute")
async def public_chat_continue(
    request: Request,
    token: str,
    data: PublicChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PublicChatResponse:
    business, call = PublicChatService.get_session_for_continue_token(db, token)
    db_history = [
        {"role": entry["role"], "content": entry["content"]}
        for entry in (call.conversation_history or [])
        if entry.get("role") in ("user", "assistant") and entry.get("content")
    ]
    client_history = [h.model_dump() for h in data.history]
    history = db_history if len(db_history) >= len(client_history) else client_history

    result = await PublicChatService.chat(
        db,
        business,
        user_message=data.message,
        history=history,
        session_id=call.id,
        customer_phone=data.customer_phone or call.caller_phone,
        existing_call=call,
    )
    background_tasks.add_task(_summarize_conversation, result["session_id"])
    return PublicChatResponse(**result)


@router.get("/address-confirm/{token}", response_model=AddressConfirmInfoResponse)
def get_address_confirm_info(
    token: str,
    db: Session = Depends(get_db),
) -> AddressConfirmInfoResponse:
    record = AddressConfirmationService.get_public_token(db, token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link invalid or expired")

    business = db.query(Business).filter(Business.id == record.business_id).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    return AddressConfirmInfoResponse(
        business_name=business.name,
        customer_name=record.customer_name,
        already_confirmed=bool(record.confirmed_at),
        confirmed_address=record.confirmed_address,
    )


@router.post("/address-confirm/{token}", response_model=AddressConfirmResponse)
def confirm_address(
    token: str,
    data: AddressConfirmRequest,
    db: Session = Depends(get_db),
) -> AddressConfirmResponse:
    ok, message = AddressConfirmationService.confirm_address(db, token, data.address)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return AddressConfirmResponse(success=True, address=message, message="Address confirmed. Thank you!")
