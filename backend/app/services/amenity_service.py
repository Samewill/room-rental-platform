from app.repositories.amenity_repository import AmenityRepository
from app.schemas.amenity import AmenityResponse


class AmenityService:
    def __init__(self, repository: AmenityRepository) -> None:
        self._repository = repository

    def list_amenities(self) -> list[AmenityResponse]:
        return [
            AmenityResponse.model_validate(amenity)
            for amenity in self._repository.list_all()
        ]
