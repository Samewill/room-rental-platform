import logging
from typing import BinaryIO

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.repositories.area_repository import AreaRepository
from app.repositories.listing_repository import ListingRepository
from app.schemas.landlord_listing import (
    ListingCreateRequest,
    ListingUpdateRequest,
)
from app.schemas.listing import ListingResponse
from app.services.photo_storage import (
    CloudinaryPhotoStorage,
    PhotoStorageError,
)


logger = logging.getLogger(__name__)


class ListingNotFoundError(Exception):
    pass


class ListingAreaNotFoundError(Exception):
    pass


class ListingStateError(Exception):
    pass


class LandlordListingService:
    DRAFT_STATUS = "draft"
    PENDING_STATUS = "pending"
    ACTIVE_STATUS = "active"
    CLOSED_STATUS = "closed"

    def __init__(
        self,
        db: Session,
        photo_storage: CloudinaryPhotoStorage | None = None,
    ) -> None:
        self._db = db
        self._listings = ListingRepository(db)
        self._areas = AreaRepository(db)
        self._photo_storage = photo_storage or CloudinaryPhotoStorage()

    def list_for_landlord(self, landlord_id: int) -> list[ListingResponse]:
        return [
            ListingResponse.model_validate(listing)
            for listing in self._listings.list_for_landlord(landlord_id)
        ]

    def create_listing(
        self,
        landlord_id: int,
        changes: ListingCreateRequest,
    ) -> ListingResponse:
        self._require_area(changes.area_id)
        listing = Listing(
            landlord_id=landlord_id,
            status=self.DRAFT_STATUS,
            **changes.model_dump(),
        )

        try:
            self._listings.add(listing)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        self._commit()
        return ListingResponse.model_validate(listing)

    def update_listing(
        self,
        landlord_id: int,
        listing_id: int,
        changes: ListingUpdateRequest,
    ) -> ListingResponse:
        listing = self._get_owned(landlord_id, listing_id)
        if listing.status == self.CLOSED_STATUS:
            raise ListingStateError("Closed listings cannot be edited.")

        updates = changes.model_dump(exclude_unset=True)
        if "area_id" in updates:
            self._require_area(updates["area_id"])
        for field_name, value in updates.items():
            setattr(listing, field_name, value)
        if listing.status in {self.PENDING_STATUS, self.ACTIVE_STATUS}:
            listing.status = self.DRAFT_STATUS

        self._commit()
        return ListingResponse.model_validate(listing)

    def submit_listing(
        self,
        landlord_id: int,
        listing_id: int,
    ) -> ListingResponse:
        listing = self._get_owned(landlord_id, listing_id)
        if listing.status == self.PENDING_STATUS:
            return ListingResponse.model_validate(listing)
        if listing.status != self.DRAFT_STATUS:
            raise ListingStateError(
                "Only draft listings can be submitted for review.",
            )

        listing.status = self.PENDING_STATUS
        self._commit()
        return ListingResponse.model_validate(listing)

    def withdraw_listing(
        self,
        landlord_id: int,
        listing_id: int,
    ) -> ListingResponse:
        listing = self._get_owned(landlord_id, listing_id)
        if listing.status != self.CLOSED_STATUS:
            listing.status = self.CLOSED_STATUS
            self._commit()
        return ListingResponse.model_validate(listing)

    def upload_photo(
        self,
        landlord_id: int,
        listing_id: int,
        image: BinaryIO,
    ) -> ListingResponse:
        listing = self._get_owned(landlord_id, listing_id)
        if listing.status == self.CLOSED_STATUS:
            raise ListingStateError("Closed listings cannot be changed.")

        stored_photo = self._photo_storage.upload(image)
        try:
            self._listings.add_photo(listing, stored_photo.url)
            if listing.status in {self.PENDING_STATUS, self.ACTIVE_STATUS}:
                listing.status = self.DRAFT_STATUS
        except SQLAlchemyError:
            self._db.rollback()
            self._cleanup_uploaded_photo(stored_photo.public_id)
            raise

        try:
            self._commit()
        except SQLAlchemyError:
            self._cleanup_uploaded_photo(stored_photo.public_id)
            raise

        return ListingResponse.model_validate(listing)

    def _get_owned(self, landlord_id: int, listing_id: int) -> Listing:
        listing = self._listings.get_owned(listing_id, landlord_id)
        if listing is None:
            raise ListingNotFoundError("Listing does not exist.")
        return listing

    def _require_area(self, area_id: int) -> None:
        if self._areas.get_by_id(area_id) is None:
            raise ListingAreaNotFoundError("Area does not exist.")

    def _commit(self) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    def _cleanup_uploaded_photo(self, public_id: str) -> None:
        try:
            self._photo_storage.delete(public_id)
        except PhotoStorageError:
            logger.exception(
                "Failed to clean up an uploaded photo after database error",
            )
