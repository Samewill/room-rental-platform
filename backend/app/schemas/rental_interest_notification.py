from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


RentalInterestNotificationEvent = Literal[
    "interest_registered",
    "interest_status_updated",
    "interest_promoted",
    "interest_expired",
    "opportunity_closed",
    "interest_withdrawn",
]


class RentalInterestNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    interest_id: int
    listing_id: int
    event_type: RentalInterestNotificationEvent
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None
