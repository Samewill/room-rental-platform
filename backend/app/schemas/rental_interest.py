from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.amenity import AmenityName
from app.schemas.landlord_listing import RoomType


class InterestOpportunityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_from: date
    available_until: date | None = None
    available_units: int | None = Field(default=None, gt=0, le=500)
    max_active_registrations: int = Field(default=50, ge=1, le=500)
    waitlist_enabled: bool = False
    expected_rental_duration_months: int | None = Field(
        default=None,
        ge=1,
        le=60,
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "InterestOpportunityRequest":
        if self.available_from < date.today():
            raise ValueError("available_from cannot be in the past.")
        if (
            self.available_until is not None
            and self.available_until < self.available_from
        ):
            raise ValueError("available_until cannot precede available_from.")
        return self


class InterestOpportunitySummary(BaseModel):
    opportunity_id: int
    listing_id: int
    listing_title: str
    address: str
    area_name: str
    room_type: RoomType
    monthly_rent: Decimal
    amenities: list[str]
    available_from: date
    available_until: date | None
    available_units: int | None
    expected_rental_duration_months: int | None


class InterestOpportunityResponse(InterestOpportunitySummary):
    status: Literal["open", "closed"]
    availability_status: Literal["open", "full", "closed"]
    max_active_registrations: int
    active_registration_count: int
    waitlist_count: int
    waitlist_enabled: bool


class RentalInterestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_move_in_date: date
    expected_duration_months: int = Field(ge=1, le=60)
    monthly_budget: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    preferred_room_type: RoomType | None = None
    required_amenities: list[AmenityName] = Field(default_factory=list, max_length=4)
    join_waitlist: bool = False

    @model_validator(mode="after")
    def validate_preferences(self) -> "RentalInterestCreateRequest":
        if self.expected_move_in_date < date.today():
            raise ValueError("expected_move_in_date cannot be in the past.")
        if len(set(self.required_amenities)) != len(self.required_amenities):
            raise ValueError("required_amenities cannot contain duplicates.")
        return self


class RentalInterestRenewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    join_waitlist: bool = False


class RentalInterestStatusHistoryResponse(BaseModel):
    from_status: str | None
    to_status: str
    changed_at: datetime
    note: str | None


class RentalInterestTenantResponse(BaseModel):
    interest_id: int
    opportunity: InterestOpportunitySummary
    expected_move_in_date: date
    expected_duration_months: int
    monthly_budget: Decimal
    preferred_room_type: RoomType | None
    required_amenities: list[str]
    status: str
    reservation_confirmed: Literal[False] = False
    registered_at: datetime
    expires_at: datetime
    history: list[RentalInterestStatusHistoryResponse]


class RentalInterestLandlordResponse(RentalInterestTenantResponse):
    tenant_name: str
    compatibility_score: int
    compatibility_reasons: list[str]


class RentalInterestStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["contacted", "invited_to_apply", "converted"]
