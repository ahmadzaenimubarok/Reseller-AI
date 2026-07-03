import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_flags import FeatureStatus, check_feature_status


def _make_tenant(plan: str) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.plan = plan
    return t


def _make_credential(expired: bool = False) -> MagicMock:
    c = MagicMock()
    c.is_expired.return_value = expired
    return c


@pytest.mark.asyncio
async def test_plan_locked_when_feature_not_in_plan():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("free")

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False):
        status = await check_feature_status(tenant_id, "product_discovery", db)

    assert status == FeatureStatus.PLAN_LOCKED


@pytest.mark.asyncio
async def test_not_configured_when_no_credential():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=None):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_expired_when_credential_expired():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")
    credential = _make_credential(expired=True)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.EXPIRED


@pytest.mark.asyncio
async def test_active_when_everything_ok():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")
    credential = _make_credential(expired=False)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.ACTIVE


@pytest.mark.asyncio
async def test_not_configured_when_tenant_not_found():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    with patch("app.core.feature_flags._get_tenant", return_value=None):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_safe_default_on_exception():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    with patch("app.core.feature_flags._get_tenant", side_effect=Exception("DB down")):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_enterprise_plan_has_all_features():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("enterprise")
    credential = _make_credential(expired=False)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "any_future_feature", db)

    assert status == FeatureStatus.ACTIVE
