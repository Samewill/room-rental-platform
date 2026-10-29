from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


ListingTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
ListingDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
ListingAddress = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
RoomType = Literal[
    "single_room",
    "shared_room",
    "bachelor_flat",
    "self_contained",
]
MonthlyRent = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
]
DepositAmount = Annotated[
    Decimal,
    Field(ge=0, max_digits=10, decimal_places=2),
]


class ListingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: int = Field(gt=0)
    title: ListingTitle
    description: ListingDescription
    room_type: RoomType
    monthly_rent: MonthlyRent
    deposit_amount: DepositAmount
    address: ListingAddress
    date_available: date


class ListingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: int | None = Field(default=None, gt=0)
    title: ListingTitle | None = None
    description: ListingDescription | None = None
    room_type: RoomType | None = None
    monthly_rent: MonthlyRent | None = None
    deposit_amount: DepositAmount | None = None
    address: ListingAddress | None = None
    date_available: date | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> "ListingUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one listing field to update.")
        if any(
            getattr(self, field_name) is None
            for field_name in self.model_fields_set
        ):
            raise ValueError("Listing fields cannot be null.")
        return self
