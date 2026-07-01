"""Unified conversation inbox — list and detail for owner dashboard."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import ConversationDetailResponse, ConversationListItem
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ConversationListItem]:
    return ConversationService.list_conversations(db, business.id, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    detail = ConversationService.get_conversation(db, business.id, conversation_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return detail
