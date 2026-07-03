import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import create_access_token
from app.main import app


def _make_access_token(tenant_id: str) -> str:
    return create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "role": "tenant_user",
    })


def _make_conv(tenant_id: str, is_human_takeover: bool = False) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.tenant_id = uuid.UUID(tenant_id)
    c.customer_id = uuid.uuid4()
    c.platform = "facebook"
    c.channel_type = "comment"
    c.message_in = "Harga berapa?"
    c.message_out = "Rp 150.000 kak!"
    c.intent = "tanya_info"
    c.sentiment = "neutral"
    c.is_human_takeover = is_human_takeover
    c.escalation_reason = None
    c.created_at = datetime.now(timezone.utc)
    return c


def test_list_conversations_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/api/v1/conversations")
    assert res.status_code == 401


def _make_db_override(mock_session: AsyncMock):
    from fastapi import Request as FastAPIRequest
    async def override_db(request: FastAPIRequest):
        yield mock_session
    return override_db


def test_list_conversations_returns_list():
    tenant_id = str(uuid.uuid4())
    token = _make_access_token(tenant_id)
    conv = _make_conv(tenant_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [conv]
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db_session] = _make_db_override(mock_session)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get(
                "/api/v1/conversations",
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 200
    assert res.json()["success"] is True
    assert isinstance(res.json()["data"], list)


def test_toggle_takeover_not_found():
    tenant_id = str(uuid.uuid4())
    token = _make_access_token(tenant_id)
    conv_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db_session] = _make_db_override(mock_session)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.patch(
                f"/api/v1/conversations/{conv_id}/takeover",
                headers={"Authorization": f"Bearer {token}"},
                json={"is_human_takeover": False},
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 404


def test_toggle_takeover_success():
    tenant_id = str(uuid.uuid4())
    token = _make_access_token(tenant_id)
    conv = _make_conv(tenant_id, is_human_takeover=True)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = conv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db_session] = _make_db_override(mock_session)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.patch(
                f"/api/v1/conversations/{conv.id}/takeover",
                headers={"Authorization": f"Bearer {token}"},
                json={"is_human_takeover": False},
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["is_human_takeover"] is False
