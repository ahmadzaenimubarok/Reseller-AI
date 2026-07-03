import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

logger = logging.getLogger(__name__)

MAX_PRODUCTS = 5


async def get_product_context(
    tenant_id: str, query: str, db: AsyncSession
) -> str:
    """
    Kembalikan konteks produk sebagai teks untuk RAG prompt.
    Fase 2: keyword fallback — ambil produk aktif tenant (maks 5).
    Fase 4: ganti dengan pgvector similarity search.
    """
    try:
        result = await db.execute(
            select(Product)
            .where(
                Product.tenant_id == uuid.UUID(tenant_id),
                Product.status == "active",
            )
            .limit(MAX_PRODUCTS)
        )
        products = result.scalars().all()

        if not products:
            return ""

        lines = []
        for p in products:
            parts = [f"Produk: {p.name}"]
            if p.description:
                parts.append(f"Deskripsi: {p.description}")
            if p.base_price:
                parts.append(f"Harga: Rp {int(p.base_price):,}")
            if p.affiliate_link:
                parts.append(f"Link beli: {p.affiliate_link}")
            lines.append(" | ".join(parts))

        return "\n".join(lines)

    except Exception:
        logger.exception("get_product_context error", extra={"tenant_id": tenant_id})
        return ""
