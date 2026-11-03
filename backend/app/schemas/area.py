from pydantic import BaseModel, ConfigDict, Field


class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_id: int
    name: str = Field(max_length=150)
