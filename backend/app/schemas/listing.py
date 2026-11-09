from datetime import date, datetime
from decimal import Decimal

from pydantic import AliasPath, BaseModel, ConfigDict, Field


class ListingPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    photo_id: int
    url: str = Field(max_length=500)
    uploaded_at: datetime


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listing_id: int
    area_id: int
    area_name: str | None = Field(
        default=None,
        validation_alias=AliasPath("area", "name"),
    )
    title: str = Field(max_length=150)
    description: str
    room_type: str = Field(max_length=14)
    monthly_rent: Decimal = Field(max_digits=10, decimal_places=2)
    deposit_amount: Decimal = Field(max_digits=10, decimal_places=2)
    address: str = Field(max_length=255)
    date_available: date
    status: str = Field(max_length=7)
    created_at: datetime
    photos: list[ListingPhotoResponse] = Field(default_factory=list)
    amenities: list[str] = Field(
        default_factory=list,
        validation_alias="amenity_names",
    )


class LandlordListingResponse(ListingResponse):
    google_place_id: str | None = Field(
        default=None,
        max_length=512,
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        allow_inf_nan=False,
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        allow_inf_nan=False,
    )


class PublicListingResponse(ListingResponse):
    has_map_location: bool = False
    approximate_latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        allow_inf_nan=False,
    )
    approximate_longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        allow_inf_nan=False,
    )
