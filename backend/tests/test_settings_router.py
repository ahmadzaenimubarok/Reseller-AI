from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def auth_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/api/v1/auth/register", json={
            "name": "Settings Test",
            "email": "settingstest_ig@test.com",
            "password": "Test1234!",
        })
        c.post("/api/v1/auth/login", json={
            "email": "settingstest_ig@test.com",
            "password": "Test1234!",
        })
        yield c


def test_instagram_token_endpoint_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        res = c.post("/api/v1/settings/instagram-token", json={
            "page_token": "EAAxxxxxxxxxxxxxxx",
            "instagram_account_id": "123456789",
        })
    assert res.status_code == 401


def test_instagram_token_endpoint_saves_token(auth_client):
    with patch("app.routers.settings.save_ig_token", new_callable=AsyncMock) as mock_save:
        res = auth_client.post("/api/v1/settings/instagram-token", json={
            "page_token": "EAAxxxxxxxxxxxxxxx",
            "instagram_account_id": "123456789",
        })

    assert res.status_code == 200
    assert res.json()["message"] == "Instagram token saved successfully."
    mock_save.assert_called_once()


def test_instagram_token_endpoint_rejects_short_token(auth_client):
    res = auth_client.post("/api/v1/settings/instagram-token", json={
        "page_token": "short",
        "instagram_account_id": "123456789",
    })
    assert res.status_code == 422


def test_instagram_token_endpoint_rejects_missing_account_id(auth_client):
    res = auth_client.post("/api/v1/settings/instagram-token", json={
        "page_token": "EAAxxxxxxxxxxxxxxx",
    })
    assert res.status_code == 422
