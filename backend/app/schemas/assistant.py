from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.listing import ListingResponse


AssistantRole = Literal["tenant", "landlord"]
AssistantMessageContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class AssistantConversationCreateRequest(BaseModel):
    assistant_role: AssistantRole


class AssistantMessageCreateRequest(BaseModel):
    content: AssistantMessageContent


class AssistantListingResult(BaseModel):
    listing: ListingResponse
    area_name: str


class AssistantNotification(BaseModel):
    kind: Literal["listing_approved", "listing_rejected"]
    listing_id: int
    listing_title: str
    reason: str | None = None


class AssistantDraftResponse(BaseModel):
    area_id: int | None = None
    area_name: str | None = None
    title: str | None = None
    description: str | None = None
    room_type: str | None = None
    monthly_rent: str | None = None
    deposit_amount: str | None = None
    address: str | None = None
    date_available: str | None = None
    amenities: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    ready_to_confirm: bool = False


class AssistantMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    sender_role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    listings: list[AssistantListingResult] = Field(default_factory=list)
    draft: AssistantDraftResponse | None = None
    created_listing: ListingResponse | None = None
    notification: AssistantNotification | None = None


class AssistantConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    assistant_role: AssistantRole
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None


class AssistantConversationDetailResponse(AssistantConversationResponse):
    messages: list[AssistantMessageResponse] = Field(default_factory=list)


class AssistantConfirmListingResponse(BaseModel):
    conversation_id: int
    listing: ListingResponse
