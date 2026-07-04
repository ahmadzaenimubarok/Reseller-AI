import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.lead_service import _calculate_tier


def _conv(intent: str, sentiment: str = "neutral") -> MagicMock:
    c = MagicMock()
    c.intent = intent
    c.sentiment = sentiment
    return c


def test_calculate_tier_hot():
    convs = [_conv("niat_beli", "positive")]
    tier, reason = _calculate_tier(convs)
    assert tier == "hot"
    assert reason == "niat_beli:positive"


def test_calculate_tier_hot_beats_warm():
    convs = [_conv("tanya_info"), _conv("tanya_info"), _conv("niat_beli", "positive")]
    tier, reason = _calculate_tier(convs)
    assert tier == "hot"


def test_calculate_tier_warm_niat_beli_neutral():
    convs = [_conv("niat_beli", "neutral")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"
    assert reason == "niat_beli:neutral"


def test_calculate_tier_warm_niat_beli_negative():
    convs = [_conv("niat_beli", "negative")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"


def test_calculate_tier_warm_repeat_tanya_info():
    convs = [_conv("tanya_info"), _conv("tanya_info")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"
    assert reason == "tanya_info:2x"


def test_calculate_tier_cold_spam_only():
    convs = [_conv("spam"), _conv("spam")]
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"
    assert reason == "spam_only"


def test_calculate_tier_cold_single_tanya_info():
    convs = [_conv("tanya_info")]
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"
    assert reason == "single_interaction"


def test_calculate_tier_cold_empty():
    tier, reason = _calculate_tier([])
    assert tier == "cold"
    assert reason == "no_interactions"


def test_calculate_tier_ignores_none_intent():
    convs = [_conv(None, None), _conv("tanya_info")]  # type: ignore
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"  # hanya 1 valid tanya_info


# --- upsert_lead tests ---

from app.models.lead import Lead


@pytest.mark.asyncio
async def test_upsert_lead_creates_new():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    tenant_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    conv = _conv("niat_beli", "positive")
    conv.created_at = datetime.now(timezone.utc)

    with patch("app.services.lead_service._fetch_conversations", return_value=[conv]), \
         patch("app.services.lead_service._fetch_lead", return_value=None):
        from app.services.lead_service import upsert_lead
        result = await upsert_lead(tenant_id, customer_id, db)

    db.add.assert_called_once()
    added: Lead = db.add.call_args[0][0]
    assert added.tier == "hot"
    assert added.tier_reason == "niat_beli:positive"
    assert added.interaction_count == 1


@pytest.mark.asyncio
async def test_upsert_lead_updates_existing():
    db = AsyncMock()
    db.add = MagicMock()

    tenant_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    conv = _conv("niat_beli", "positive")
    conv.created_at = datetime.now(timezone.utc)

    existing = MagicMock(spec=Lead)
    existing.tier = "cold"

    with patch("app.services.lead_service._fetch_conversations", return_value=[conv]), \
         patch("app.services.lead_service._fetch_lead", return_value=existing):
        from app.services.lead_service import upsert_lead
        result = await upsert_lead(tenant_id, customer_id, db)

    assert existing.tier == "hot"
    assert existing.interaction_count == 1
    db.add.assert_not_called()


# --- run_decay test ---

@pytest.mark.asyncio
async def test_run_decay_hot_to_warm():
    from datetime import timedelta
    from app.services.lead_service import run_decay

    db = AsyncMock()
    now = datetime.now(timezone.utc)

    hot_lead = MagicMock(spec=Lead)
    hot_lead.tier = "hot"
    hot_lead.status = "active"
    hot_lead.last_interaction = now - timedelta(days=2)

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalars.return_value.all.return_value = [hot_lead]
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db.execute = mock_execute
    count = await run_decay(db)
    assert hot_lead.tier == "warm"
    assert count >= 1
