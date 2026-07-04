import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


async def send_comment_reply(page_token: str, comment_id: str, message: str) -> bool:
    """Balas komentar Facebook via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={"message": message},
            )
            response.raise_for_status()
            logger.info("Comment reply sent", extra={"comment_id": comment_id})
            return True
    except Exception:
        logger.exception("send_comment_reply failed", extra={"comment_id": comment_id})
        return False


async def get_messenger_user_name(page_token: str, psid: str) -> str | None:
    """Fetch nama user Messenger via Graph API pakai PSID. Return None jika gagal."""
    url = f"{GRAPH_API_BASE}/{psid}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                params={"access_token": page_token, "fields": "name"},
            )
            if response.is_success:
                return response.json().get("name")
    except Exception:
        logger.warning("get_messenger_user_name failed", extra={"psid": psid})
    return None


async def send_messenger_reply(page_token: str, recipient_id: str, message: str) -> bool:
    """Kirim pesan Messenger via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/me/messages"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                },
            )
            if not response.is_success:
                logger.error(
                    f"send_messenger_reply failed status={response.status_code} body={response.text!r}"
                )
                return False
            logger.info("Messenger reply sent", extra={"recipient_id": recipient_id})
            return True
    except Exception:
        logger.exception("send_messenger_reply failed", extra={"recipient_id": recipient_id})
        return False
