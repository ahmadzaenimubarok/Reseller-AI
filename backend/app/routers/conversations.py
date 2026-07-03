import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.conversation import Conversation
from app.schemas.base import APIResponse
from app.schemas.conversation import ConversationResponse, TakeoverRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=APIResponse[list[ConversationResponse]])
async def list_conversations(
    request: Request,
    is_human_takeover: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == uuid.UUID(tenant_id))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    if is_human_takeover is not None:
        stmt = stmt.where(Conversation.is_human_takeover == is_human_takeover)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return APIResponse(data=[ConversationResponse.model_validate(c) for c in conversations])


@router.patch("/{conversation_id}/takeover", response_model=APIResponse[ConversationResponse])
async def toggle_takeover(
    conversation_id: uuid.UUID,
    body: TakeoverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan.")

    conv.is_human_takeover = body.is_human_takeover
    if not body.is_human_takeover:
        conv.escalation_reason = None

    logger.info(
        "Takeover toggled",
        extra={
            "tenant_id": tenant_id,
            "conversation_id": str(conversation_id),
            "is_human_takeover": body.is_human_takeover,
        },
    )
    return APIResponse(data=ConversationResponse.model_validate(conv))
