"""Unified conversation inbox — list and detail for owner dashboard."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import ConversationDetailResponse, ConversationListItem, PaginatedResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=PaginatedResponse[ConversationListItem])
def list_conversations(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ConversationListItem]:
    offset = (page - 1) * page_size
    items, total = ConversationService.list_conversations_paginated(
        db, business.id, limit=page_size, offset=offset
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_more=(offset + page_size) < total,
    )


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
