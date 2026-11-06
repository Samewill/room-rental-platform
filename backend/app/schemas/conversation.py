from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_serializer,
    field_validator,
)

from app.core.whatsapp_privacy import (
    contains_phone_number,
    redact_phone_numbers,
)


MessageContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class MessageCreateRequest(BaseModel):
    content: MessageContent

    @field_validator("content")
    @classmethod
    def reject_phone_numbers(cls, content: str) -> str:
        if contains_phone_number(content):
            raise ValueError("Phone numbers cannot be shared in messages.")
        return content


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    contact_request_id: int
    created_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    conversation_id: int
    sender_id: int
    content: str
    status: Literal["sent", "read"]
    sent_at: datetime
    read_at: datetime | None
    whatsapp_delivery_status: Literal["sent", "failed"] | None = None

    @field_serializer("content")
    def serialize_content(self, content: str) -> str:
        return redact_phone_numbers(content)
