from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


ReportReason = Literal[
    "scam",
    "fake_listing",
    "inaccurate_info",
    "abusive",
    "other",
]
ReportStatus = Literal["open", "under_review", "resolved", "dismissed"]
ReportTarget = Literal["listing", "landlord", "user"]
ReportDetails = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=10, max_length=2000),
]
ReportNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ReportCreateRequest(BaseModel):
    target: ReportTarget
    listing_id: int | None = Field(default=None, gt=0)
    target_user_id: int | None = Field(default=None, gt=0)
    reason: ReportReason
    details: ReportDetails

    @model_validator(mode="after")
    def validate_target(self) -> "ReportCreateRequest":
        if self.target in {"listing", "landlord"}:
            if self.listing_id is None or self.target_user_id is not None:
                raise ValueError(
                    "Listing and landlord reports require a listing_id only.",
                )
        elif self.target_user_id is None:
            raise ValueError("User reports require a target_user_id.")
        return self


class ReportResolutionRequest(BaseModel):
    note: ReportNote | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int = Field(gt=0)
    listing_id: int | None = Field(default=None, gt=0)
    target_user_id: int | None = Field(default=None, gt=0)
    tenant_id: int = Field(gt=0)
    admin_id: int | None = Field(default=None, gt=0)
    reason: ReportReason
    status: ReportStatus
    details: str | None
    created_at: datetime


class ReportHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int = Field(gt=0)
    report_id: int = Field(gt=0)
    actor_user_id: int = Field(gt=0)
    action: Literal["submitted", "assigned", "resolved", "dismissed"]
    note: str | None
    created_at: datetime
