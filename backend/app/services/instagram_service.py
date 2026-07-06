import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


async def get_instagram_user_name(page_token: str, igsid: str) -> str | None:
    """Fetch nama/username user Instagram via Graph API. Return None jika gagal."""
    url = f"{GRAPH_API_BASE}/{igsid}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                params={"access_token": page_token, "fields": "name,username"},
            )
            if response.is_success:
                data = response.json()
                return data.get("name") or data.get("username")
    except Exception:
        logger.warning("get_instagram_user_name failed", extra={"igsid": igsid})
    return None


async def send_instagram_dm(page_token: str, recipient_igsid: str, message: str) -> bool:
    """Kirim DM Instagram via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/me/messages"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={
                    "recipient": {"id": recipient_igsid},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                },
            )
            if not response.is_success:
                logger.error(
                    f"send_instagram_dm failed status={response.status_code} body={response.text!r}"
                )
                return False
            logger.info("Instagram DM sent", extra={"recipient_igsid": recipient_igsid})
            return True
    except Exception:
        logger.exception("send_instagram_dm failed", extra={"recipient_igsid": recipient_igsid})
        return False
