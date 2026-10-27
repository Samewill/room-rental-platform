from app.repositories.area_repository import AreaRepository
from app.schemas.area import AreaResponse


class AreaService:
    def __init__(self, repository: AreaRepository) -> None:
        self._repository = repository

    def list_areas(self) -> list[AreaResponse]:
        return [
            AreaResponse.model_validate(area)
            for area in self._repository.list_all()
        ]
