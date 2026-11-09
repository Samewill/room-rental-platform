from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)


AreaName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_id: int
    name: str = Field(max_length=150)


class AreaResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AreaName
