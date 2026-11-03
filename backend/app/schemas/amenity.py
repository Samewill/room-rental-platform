from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AmenityName = Literal["Wi-Fi", "Parking", "Furnished", "Laundry"]


class AmenityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amenity_id: int
    name: str = Field(max_length=100)
