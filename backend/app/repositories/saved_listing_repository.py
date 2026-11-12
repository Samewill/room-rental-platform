from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.saved_listing import SavedListing


class SavedListingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_tenant(self, tenant_id: int) -> list[SavedListing]:
        statement = (
            select(SavedListing)
            .where(SavedListing.tenant_id == tenant_id)
            .order_by(
                SavedListing.created_at.desc(),
                SavedListing.saved_listing_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def get_for_tenant(
        self,
        tenant_id: int,
        listing_id: int,
    ) -> SavedListing | None:
        statement = select(SavedListing).where(
            SavedListing.tenant_id == tenant_id,
            SavedListing.listing_id == listing_id,
        )
        return self._db.scalar(statement)

    def add(self, saved_listing: SavedListing) -> SavedListing:
        self._db.add(saved_listing)
        self._db.flush()
        return saved_listing

    def delete(self, saved_listing: SavedListing) -> None:
        self._db.delete(saved_listing)
