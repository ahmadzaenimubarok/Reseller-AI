"""
Verifikasi RULE-03: query tidak boleh bocor lintas tenant.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_flags import FeatureStatus, check_feature_status


@pytest.mark.asyncio
async def test_feature_status_scoped_to_tenant():
    """check_feature_status tidak bisa digunakan untuk akses data tenant lain."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    db = AsyncMock()

    tenant_a_mock = MagicMock()
    tenant_a_mock.plan = "pro"

    tenant_b_mock = MagicMock()
    tenant_b_mock.plan = "free"

    async def get_tenant_by_id(tenant_id, db):
        if tenant_id == tenant_a:
            return tenant_a_mock
        return tenant_b_mock

    with patch("app.core.feature_flags._get_tenant", side_effect=get_tenant_by_id), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=None):
        # whatsapp_reply: ada di plan pro, tidak ada di plan free, butuh credential
        status_a = await check_feature_status(tenant_a, "whatsapp_reply", db)
        status_b = await check_feature_status(tenant_b, "whatsapp_reply", db)

    # Tenant A (pro): fitur tersedia di plan, tapi credential belum dikonfigurasi
    assert status_a == FeatureStatus.NOT_CONFIGURED
    # Tenant B (free): fitur tidak tersedia di plan ini
    assert status_b == FeatureStatus.PLAN_LOCKED


@pytest.mark.asyncio
async def test_tenant_provisioning_creates_isolated_workspace():
    """Setiap tenant mendapat data independen — tidak sharing state."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    from app.services.tenant_service import provision_tenant

    tenant1 = await provision_tenant("Toko A", "a@test.com", db)
    tenant2 = await provision_tenant("Toko B", "b@test.com", db)

    # Email berbeda — data tidak dicampur
    assert tenant1.email != tenant2.email
    assert tenant1.name != tenant2.name
    assert tenant1.plan == "free"
    assert tenant2.plan == "free"
    # Objek berbeda — bukan alias yang sama
    assert tenant1 is not tenant2


@pytest.mark.asyncio
async def test_different_tenants_get_independent_ai_config():
    """ai_config tiap tenant independen, tidak shared reference."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    from app.services.tenant_service import provision_tenant

    t1 = await provision_tenant("Toko A", "a@test.com", db)
    t2 = await provision_tenant("Toko B", "b@test.com", db)

    # Mutasi config tenant 1 tidak boleh mempengaruhi tenant 2
    t1.ai_config["tone"] = "formal"
    assert t2.ai_config.get("tone") != "formal"
