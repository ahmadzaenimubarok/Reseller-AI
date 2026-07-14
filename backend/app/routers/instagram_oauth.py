import base64
import json
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.instagram_oauth import InstagramConnectRequest
from app.services.instagram_oauth_service import (
    disconnect_instagram_connection,
    exchange_code_for_token,
    exchange_to_long_lived_token,
    get_instagram_accounts_for_pages,
    get_user_pages,
    save_instagram_connection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/instagram", tags=["instagram-oauth"])


@router.get("/login")
async def instagram_login(request: Request):
    """Generate Instagram OAuth URL for redirect."""
    settings = get_settings()
    tenant_id: str = request.state.tenant_id

    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_IG_REDIRECT_URI,
        "scope": "pages_show_list,instagram_basic,instagram_manage_messages",
        "response_type": "code",
        "state": tenant_id,
    }
    url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"
    return {"url": url}


@router.get("/callback")
async def instagram_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
):
    """
    Backend callback endpoint — called by Meta after user authorize.
    Exchange code → token → get pages → check IG accounts → redirect to frontend.
    """
    settings = get_settings()

    if error:
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error}"
        return RedirectResponse(url=frontend_url)

    if not code:
        error_msg = "no_code"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 1. Exchange code → short-lived token
    short_token_data = await exchange_code_for_token(code)
    if not short_token_data:
        error_msg = "exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 2. Exchange → long-lived token
    long_token_data = await exchange_to_long_lived_token(short_token_data["access_token"])
    if not long_token_data:
        error_msg = "long_lived_exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    long_token = long_token_data["access_token"]

    # 3. Get Pages list
    pages = await get_user_pages(long_token)

    # 4. For each page, check if it has Instagram Business Account
    ig_accounts = await get_instagram_accounts_for_pages(long_token, pages)

    # 5. Encode data and redirect to frontend
    callback_data = {
        "state": state,
        "accounts": ig_accounts,
    }

    encoded_data = base64.urlsafe_b64encode(json.dumps(callback_data).encode()).decode()
    frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?data={encoded_data}"

    return RedirectResponse(url=frontend_url)


@router.post("/connect")
async def instagram_connect(
    body: InstagramConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Save Instagram connection to tenant."""
    tenant_id: str = request.state.tenant_id

    await save_instagram_connection(
        tenant_id=tenant_id,
        page_id=body.page_id,
        page_token=body.page_token,
        ig_account_id=body.instagram_account_id,
        db=db,
    )

    return {
        "message": "Instagram connected successfully.",
        "instagram_account_id": body.instagram_account_id,
    }


@router.delete("/disconnect")
async def instagram_disconnect(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Remove Instagram connection for tenant."""
    tenant_id: str = request.state.tenant_id
    await disconnect_instagram_connection(tenant_id, db)

    return {"message": "Instagram connection removed successfully."}
