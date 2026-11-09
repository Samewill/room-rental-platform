from pydantic import BaseModel, Field


class PublicListingLocationResponse(BaseModel):
    approximate_latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    approximate_longitude: float = Field(
        ge=-180,
        le=180,
        allow_inf_nan=False,
    )
