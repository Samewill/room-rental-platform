from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch
from app.repositories.amenity_repository import AmenityRepository
from app.repositories.saved_search_repository import SavedSearchRepository
from app.schemas.saved_search import SavedSearchCreateRequest


class SavedSearchAmenityNotFoundError(Exception):
    pass


class SavedSearchService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._saved_searches = SavedSearchRepository(db)
        self._amenities = AmenityRepository(db)

    def create_for_tenant(
        self,
        tenant_id: int,
        request: SavedSearchCreateRequest,
    ) -> SavedSearch:
        amenities = self._amenities.get_by_names(request.amenities)
        if {amenity.name for amenity in amenities} != set(request.amenities):
            raise SavedSearchAmenityNotFoundError(
                "One or more selected amenities are unavailable.",
            )
        saved_search = SavedSearch(
            tenant_id=tenant_id,
            **request.model_dump(exclude={"amenities"}),
            amenities=amenities,
        )
        try:
            self._saved_searches.add(saved_search)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return saved_search

    def list_for_tenant(self, tenant_id: int) -> list[SavedSearch]:
        return self._saved_searches.list_for_tenant(tenant_id)

    def delete_for_tenant(self, tenant_id: int, saved_search_id: int) -> bool:
        try:
            deleted = self._saved_searches.delete_for_tenant(
                saved_search_id,
                tenant_id,
            )
            if deleted:
                self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return deleted
