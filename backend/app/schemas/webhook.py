from typing import Any

from pydantic import BaseModel


class FacebookWebhookPayload(BaseModel):
    object: str
    entry: list[dict[str, Any]]
