from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ReviewComment = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ReviewCreateRequest(BaseModel):
    contact_request_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: ReviewComment | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: int
    contact_request_id: int
    rating: int
    comment: str | None
    created_at: datetime
