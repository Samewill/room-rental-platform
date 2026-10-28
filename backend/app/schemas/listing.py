from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ListingPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    photo_id: int
    url: str = Field(max_length=500)
    uploaded_at: datetime


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listing_id: int
    area_id: int
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
