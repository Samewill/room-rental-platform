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

    def search_areas(self, name: str, limit: int = 10) -> list[AreaResponse]:
        return [
            AreaResponse.model_validate(area)
            for area in self._repository.search_by_name(name, limit)
        ]

    def resolve_area(self, name: str) -> AreaResponse:
        area = self._repository.get_or_create(name.strip())
        return AreaResponse.model_validate(area)
