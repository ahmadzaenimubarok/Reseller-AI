import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rag_service import get_product_context


@pytest.mark.asyncio
async def test_get_product_context_returns_string_with_products():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    mock_product = MagicMock()
    mock_product.name = "Tas Rajut Aesthetic"
    mock_product.description = "Tas rajut handmade, tersedia 5 warna"
    mock_product.base_price = 150000
    mock_product.affiliate_link = "https://shopee.co.id/tas-rajut"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_product]
    db.execute = AsyncMock(return_value=mock_result)

    context = await get_product_context(tenant_id, "tas rajut", db)

    assert "Tas Rajut Aesthetic" in context
    assert isinstance(context, str)


@pytest.mark.asyncio
async def test_get_product_context_returns_empty_when_no_products():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    context = await get_product_context(tenant_id, "query apapun", db)

    assert context == ""


@pytest.mark.asyncio
async def test_get_product_context_safe_on_db_error():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("DB error"))
    tenant_id = str(uuid.uuid4())

    context = await get_product_context(tenant_id, "query", db)

    assert context == ""
