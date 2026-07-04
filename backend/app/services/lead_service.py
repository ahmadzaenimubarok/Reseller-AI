import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.lead import Lead

logger = logging.getLogger(__name__)


def _calculate_tier(conversations: list) -> tuple[str, str]:
    """
    Pure function — hitung tier lead dari list conversations.
    Input: list object dengan attr .intent (str|None) dan .sentiment (str|None).
    Return: (tier, tier_reason)
    """
    if not conversations:
        return "cold", "no_interactions"

    valid = [c for c in conversations if c.intent is not None]

    # HOT: ada niat_beli + positive
    for c in valid:
        if c.intent == "niat_beli" and c.sentiment == "positive":
            return "hot", "niat_beli:positive"

    # WARM: niat_beli (sentiment apapun)
    for c in valid:
        if c.intent == "niat_beli":
            return "warm", f"niat_beli:{c.sentiment or 'unknown'}"

    # WARM: tanya_info >= 2x
    tanya_count = sum(1 for c in valid if c.intent == "tanya_info")
    if tanya_count >= 2:
        return "warm", f"tanya_info:{tanya_count}x"

    # COLD: semua spam
    non_spam = [c for c in valid if c.intent != "spam"]
    if not non_spam:
        return "cold", "spam_only"

    # COLD: single interaction
    return "cold", "single_interaction"


async def _fetch_conversations(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == uuid.UUID(tenant_id),
            Conversation.customer_id == uuid.UUID(customer_id),
        )
    )
    return list(result.scalars().all())


async def _fetch_lead(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == uuid.UUID(tenant_id),
            Lead.customer_id == uuid.UUID(customer_id),
        )
    )
    return result.scalar_one_or_none()


async def upsert_lead(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> Lead:
    conversations = await _fetch_conversations(tenant_id, customer_id, db)
    tier, tier_reason = _calculate_tier(conversations)

    last_interaction = None
    if conversations:
        last_interaction = max(
            (c.created_at for c in conversations if c.created_at), default=None
        )

    interaction_count = len(conversations)
    existing = await _fetch_lead(tenant_id, customer_id, db)

    if existing is None:
        lead = Lead(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=uuid.UUID(customer_id),
            tier=tier,
            tier_reason=tier_reason,
            interaction_count=interaction_count,
            last_interaction=last_interaction,
            status="active",
        )
        db.add(lead)
        logger.info(
            "Lead created",
            extra={"tenant_id": tenant_id, "customer_id": customer_id, "tier": tier},
        )
        return lead

    existing.tier = tier
    existing.tier_reason = tier_reason
    existing.interaction_count = interaction_count
    existing.last_interaction = last_interaction
    logger.info(
        "Lead updated",
        extra={"tenant_id": tenant_id, "customer_id": customer_id, "tier": tier},
    )
    return existing


async def archive_lead(
    lead_id: uuid.UUID, tenant_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        return None
    lead.status = "archived"
    logger.info("Lead archived", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    return lead


async def resolve_lead(
    lead_id: uuid.UUID, tenant_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        return None
    lead.status = "resolved"
    lead.resolved_at = datetime.now(timezone.utc)
    logger.info("Lead resolved", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    return lead


async def run_decay(db: AsyncSession) -> int:
    """
    Auto-decay tiers berdasarkan last_interaction.
    Return jumlah lead yang di-update.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    count = 0

    # hot → warm: tidak aktif > 1 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "hot",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=1),
        )
    )
    for lead in result.scalars().all():
        lead.tier = "warm"
        lead.tier_reason = "decayed:hot_to_warm"
        count += 1

    # warm → cold: tidak aktif > 2 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "warm",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=2),
        )
    )
    for lead in result.scalars().all():
        lead.tier = "cold"
        lead.tier_reason = "decayed:warm_to_cold"
        count += 1

    # cold → archived: tidak aktif > 7 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "cold",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=7),
        )
    )
    for lead in result.scalars().all():
        lead.status = "archived"
        count += 1

    logger.info("Lead decay completed", extra={"updated_count": count})
    return count
