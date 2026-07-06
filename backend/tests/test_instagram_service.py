import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.instagram_service import get_instagram_user_name, send_instagram_dm


@pytest.mark.asyncio
async def test_get_instagram_user_name_returns_name():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"name": "Budi Santoso", "username": "budi.s"}

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token123", "igsid-abc")

    assert result == "Budi Santoso"


@pytest.mark.asyncio
async def test_get_instagram_user_name_falls_back_to_username():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"username": "budi.s"}

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token123", "igsid-abc")

    assert result == "budi.s"


@pytest.mark.asyncio
async def test_get_instagram_user_name_returns_none_on_error():
    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token", "igsid")

    assert result is None


@pytest.mark.asyncio
async def test_send_instagram_dm_success():
    mock_response = MagicMock()
    mock_response.is_success = True

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token123", "igsid-abc", "Halo kak!")

    assert result is True


@pytest.mark.asyncio
async def test_send_instagram_dm_returns_false_on_error():
    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token", "igsid", "pesan")

    assert result is False


@pytest.mark.asyncio
async def test_send_instagram_dm_returns_false_on_non_success_status():
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token", "igsid", "pesan")

    assert result is False
