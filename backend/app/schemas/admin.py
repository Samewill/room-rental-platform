from typing import Literal

from pydantic import BaseModel, Field


class LandlordRoleGrantResponse(BaseModel):
    user_id: int = Field(gt=0)
    role: Literal["landlord"] = "landlord"
    granted: bool
