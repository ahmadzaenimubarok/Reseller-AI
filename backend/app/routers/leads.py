import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.customer import Customer
from app.models.lead import Lead
from app.schemas.base import APIResponse
from app.schemas.lead import LeadResponse
from app.services.lead_service import archive_lead, resolve_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


async def _enrich_leads(leads: list[Lead], tenant_id: str, db: AsyncSession) -> list[LeadResponse]:
    """Join customer name & platform ke lead response."""
    customer_ids = [l.customer_id for l in leads]
    customers: dict[uuid.UUID, Customer] = {}
    if customer_ids:
        result = await db.execute(
            select(Customer).where(
                Customer.tenant_id == uuid.UUID(tenant_id),
                Customer.id.in_(customer_ids),
            )
        )
        for c in result.scalars().all():
            customers[c.id] = c

    out = []
    for lead in leads:
        cust = customers.get(lead.customer_id)
        data = LeadResponse.model_validate(lead)
        data.customer_name = cust.name if cust else None
        data.customer_platform = cust.platform if cust else None
        out.append(data)
    return out


@router.get("", response_model=APIResponse[list[LeadResponse]])
async def list_leads(
    request: Request,
    tier: str | None = Query(None, description="hot | warm | cold"),
    status: str | None = Query(None, description="active | archived | resolved"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    stmt = (
        select(Lead)
        .where(Lead.tenant_id == uuid.UUID(tenant_id))
        .order_by(Lead.updated_at.desc())
        .limit(limit)
    )
    if tier is not None:
        stmt = stmt.where(Lead.tier == tier)
    if status is not None:
        stmt = stmt.where(Lead.status == status)

    result = await db.execute(stmt)
    leads = list(result.scalars().all())

    return APIResponse(data=await _enrich_leads(leads, tenant_id, db))


@router.patch("/{lead_id}/archive", response_model=APIResponse[LeadResponse])
async def archive_lead_endpoint(
    lead_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    lead = await archive_lead(lead_id, tenant_id, db)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    logger.info("Lead archived via API", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    enriched = await _enrich_leads([lead], tenant_id, db)
    return APIResponse(data=enriched[0])


@router.patch("/{lead_id}/resolve", response_model=APIResponse[LeadResponse])
async def resolve_lead_endpoint(
    lead_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    lead = await resolve_lead(lead_id, tenant_id, db)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    logger.info("Lead resolved via API", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    enriched = await _enrich_leads([lead], tenant_id, db)
    return APIResponse(data=enriched[0])
