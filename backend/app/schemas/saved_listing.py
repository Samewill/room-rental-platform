from pydantic import BaseModel


class SavedListingStatusResponse(BaseModel):
    listing_id: int
    saved: bool
