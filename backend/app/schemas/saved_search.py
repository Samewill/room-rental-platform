from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.amenity import AmenityName

RoomType = Literal[
    "single_room",
    "shared_room",
    "bachelor_flat",
    "self_contained",
]
Location = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
Rent = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class SavedSearchCreateRequest(BaseModel):
    location: Location | None = None
    room_type: RoomType | None = None
    minimum_rent: Rent | None = None
    maximum_rent: Rent | None = None
    amenities: list[AmenityName] = Field(default_factory=list, max_length=4)
    alerts_enabled: bool = False

    @model_validator(mode="after")
    def validate_search_criteria(self) -> "SavedSearchCreateRequest":
        if not any(
            (
                self.location is not None,
                self.room_type is not None,
                self.minimum_rent is not None,
                self.maximum_rent is not None,
                bool(self.amenities),
            )
        ):
            raise ValueError("At least one search filter is required.")
        if (
            self.minimum_rent is not None
            and self.maximum_rent is not None
            and self.minimum_rent > self.maximum_rent
        ):
            raise ValueError(
                "minimum_rent must be less than or equal to maximum_rent.",
            )
        return self


class SavedSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    saved_search_id: int
    location: str | None
    room_type: RoomType | None
    minimum_rent: Decimal | None
    maximum_rent: Decimal | None
    amenities: list[str] = Field(
        default_factory=list,
        validation_alias="amenity_names",
    )
    alerts_enabled: bool = False
    created_at: datetime


class SavedSearchAlertsUpdateRequest(BaseModel):
    alerts_enabled: bool
