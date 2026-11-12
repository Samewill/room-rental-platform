from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch
from app.models.whatsapp import WhatsAppContact
from app.repositories.amenity_repository import AmenityRepository
from app.repositories.saved_search_repository import SavedSearchRepository
from app.schemas.saved_search import (
    SavedSearchAlertsUpdateRequest,
    SavedSearchCreateRequest,
)


class SavedSearchAmenityNotFoundError(Exception):
    pass


class SavedSearchWhatsAppNotEnabledError(Exception):
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
        if request.alerts_enabled and not self._whatsapp_is_enabled(tenant_id):
            raise SavedSearchWhatsAppNotEnabledError(
                "Verify and enable WhatsApp before turning on search alerts.",
            )
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
        if saved_search.alerts_enabled:
            saved_search.alerts_opted_in_at = self._now()
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

    def update_alerts_for_tenant(
        self,
        tenant_id: int,
        saved_search_id: int,
        request: SavedSearchAlertsUpdateRequest,
    ) -> SavedSearch | None:
        saved_search = self._saved_searches.get_for_tenant(
            saved_search_id,
            tenant_id,
        )
        if saved_search is None:
            return None
        if request.alerts_enabled and not self._whatsapp_is_enabled(tenant_id):
            raise SavedSearchWhatsAppNotEnabledError(
                "Verify and enable WhatsApp before turning on search alerts.",
            )

        saved_search.alerts_enabled = request.alerts_enabled
        saved_search.alerts_opted_in_at = (
            self._now() if request.alerts_enabled else None
        )
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        return saved_search

    def _whatsapp_is_enabled(self, tenant_id: int) -> bool:
        contact = self._db.get(WhatsAppContact, tenant_id)
        return (
            contact is not None
            and contact.verified_at is not None
            and contact.opted_in_at is not None
            and contact.opted_out_at is None
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
