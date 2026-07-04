import logging
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.schemas.base import APIResponse
from app.schemas.conversation import ConversationResponse, TakeoverRequest, ThreadMessage, ThreadResponse

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


@router.get("/threads", response_model=APIResponse[list[ThreadResponse]])
async def list_threads(
    request: Request,
    is_human_takeover: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """Return conversations grouped by customer (thread view)."""
    tenant_id: str = request.state.tenant_id

    # Fetch conversations
    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == uuid.UUID(tenant_id))
        .order_by(Conversation.created_at.asc())
    )
    if is_human_takeover is not None:
        stmt = stmt.where(Conversation.is_human_takeover == is_human_takeover)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    # Collect unique customer IDs
    customer_ids = list({c.customer_id for c in conversations})

    # Fetch customer data
    customers: dict[uuid.UUID, Customer] = {}
    if customer_ids:
        cust_result = await db.execute(
            select(Customer).where(
                Customer.tenant_id == uuid.UUID(tenant_id),
                Customer.id.in_(customer_ids),
            )
        )
        for cust in cust_result.scalars().all():
            customers[cust.id] = cust

    # Group conversations by customer
    grouped: dict[uuid.UUID, list[Conversation]] = defaultdict(list)
    for conv in conversations:
        grouped[conv.customer_id].append(conv)

    # Build thread responses — sort threads by most recent message
    threads: list[ThreadResponse] = []
    for customer_id, msgs in grouped.items():
        cust = customers.get(customer_id)
        last_msg = msgs[-1]
        threads.append(
            ThreadResponse(
                customer_id=customer_id,
                customer_name=cust.name if cust else None,
                platform=last_msg.platform,
                channel_type=last_msg.channel_type,
                message_count=len(msgs),
                has_human_takeover=any(m.is_human_takeover for m in msgs),
                last_message_at=last_msg.created_at,
                messages=[ThreadMessage.model_validate(m) for m in msgs],
            )
        )

    threads.sort(key=lambda t: t.last_message_at, reverse=True)
    return APIResponse(data=threads[:limit])


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
