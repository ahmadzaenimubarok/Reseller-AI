import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    platform: str
    channel_type: str
    message_in: str | None
    message_out: str | None
    intent: str | None
    sentiment: str | None
    is_human_takeover: bool
    escalation_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TakeoverRequest(BaseModel):
    is_human_takeover: bool
