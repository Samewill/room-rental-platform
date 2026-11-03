from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.amenity import Amenity
from app.models.saved_search import SavedSearch


class SavedSearchRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, saved_search: SavedSearch) -> SavedSearch:
        self._db.add(saved_search)
        self._db.flush()
        return saved_search

    def list_for_tenant(self, tenant_id: int) -> list[SavedSearch]:
        statement = (
            select(SavedSearch)
            .where(SavedSearch.tenant_id == tenant_id)
            .order_by(
                SavedSearch.created_at.desc(),
                SavedSearch.saved_search_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def delete_for_tenant(
        self,
        saved_search_id: int,
        tenant_id: int,
    ) -> bool:
        statement = select(SavedSearch).where(
            SavedSearch.saved_search_id == saved_search_id,
            SavedSearch.tenant_id == tenant_id,
        )
        saved_search = self._db.scalar(statement)
        if saved_search is None:
            return False

        self._db.delete(saved_search)
        return True
