from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ModerationDecision = Literal["approved", "rejected", "flagged"]
ModerationReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ModerationApprovalRequest(BaseModel):
    reason: str | None = None


class ModerationReasonRequest(BaseModel):
    reason: ModerationReason


class ListingModerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderation_id: int = Field(gt=0)
    listing_id: int = Field(gt=0)
    admin_id: int = Field(gt=0)
    decision: ModerationDecision
    reason: str | None
    decided_at: datetime
