from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ProfileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
ProfileBusinessName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str = Field(max_length=150)
    phone_no: str = Field(max_length=20)
    email: str = Field(max_length=255)
    business_name: str | None = Field(default=None, max_length=150)
    created_at: datetime
    roles: list[str] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: ProfileName | None = None
    business_name: ProfileBusinessName | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> "UserProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one profile field to update.")
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("full_name cannot be null.")
        return self
