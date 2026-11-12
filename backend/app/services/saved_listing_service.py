from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.saved_listing import SavedListing
from app.repositories.listing_repository import ListingRepository
from app.repositories.saved_listing_repository import SavedListingRepository
from app.schemas.listing import PublicListingResponse
from app.services.listing_service import ListingService


class SavedListingUnavailableError(Exception):
    pass


class SavedListingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._saved_listings = SavedListingRepository(db)
        self._listings = ListingService(ListingRepository(db))

    def list_for_tenant(
        self,
        tenant_id: int,
    ) -> list[PublicListingResponse]:
        saved = self._saved_listings.list_for_tenant(tenant_id)
        listings = []
        for item in saved:
            listing = self._listings.get_public_listing(item.listing_id)
            if listing is not None:
                listings.append(listing)
        return listings

    def is_saved(self, tenant_id: int, listing_id: int) -> bool:
        return (
            self._saved_listings.get_for_tenant(tenant_id, listing_id)
            is not None
        )

    def save_for_tenant(self, tenant_id: int, listing_id: int) -> bool:
        if self._listings.get_public_listing(listing_id) is None:
            raise SavedListingUnavailableError(
                "Only currently available public rooms can be saved.",
            )
        if self._saved_listings.get_for_tenant(tenant_id, listing_id) is not None:
            return False

        try:
            self._saved_listings.add(
                SavedListing(tenant_id=tenant_id, listing_id=listing_id),
            )
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            if self._saved_listings.get_for_tenant(tenant_id, listing_id):
                return False
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise
        return True

    def remove_for_tenant(self, tenant_id: int, listing_id: int) -> bool:
        saved = self._saved_listings.get_for_tenant(tenant_id, listing_id)
        if saved is None:
            return False
        try:
            self._saved_listings.delete(saved)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        return True
