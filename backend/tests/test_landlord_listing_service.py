import unittest
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from app.models.listing import Listing, ListingPhoto
from app.schemas.landlord_listing import (
    ListingCreateRequest,
    ListingUpdateRequest,
)
from app.services.landlord_listing_service import (
    LandlordListingService,
    ListingAreaNotFoundError,
    ListingNotFoundError,
    ListingStateError,
)
from app.services.photo_storage import StoredPhoto


class LandlordListingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.listings = Mock()
        self.areas = Mock()
        self.photo_storage = Mock()
        self.service = LandlordListingService(self.db, self.photo_storage)
        self.service._listings = self.listings
        self.service._areas = self.areas
        self.areas.get_by_id.return_value = object()

    @staticmethod
    def make_listing(
        *,
        listing_id: int = 12,
        landlord_id: int = 8,
        status: str = "draft",
    ) -> Listing:
        return Listing(
            listing_id=listing_id,
            landlord_id=landlord_id,
            area_id=3,
            title="A room",
            description="A room description",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date(2026, 11, 1),
            status=status,
            created_at=datetime(2026, 10, 1),
        )

    @staticmethod
    def create_request() -> ListingCreateRequest:
        return ListingCreateRequest(
            area_id=3,
            title="A room",
            description="A room description",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date(2026, 11, 1),
        )

    def test_create_assigns_landlord_and_starts_as_draft(self) -> None:
        def add_listing(listing: Listing) -> Listing:
            listing.listing_id = 12
            listing.created_at = datetime(2026, 10, 1)
            return listing

        self.listings.add.side_effect = add_listing

        result = self.service.create_listing(8, self.create_request())

        self.assertEqual(result.listing_id, 12)
        self.assertEqual(result.status, "draft")
        self.assertEqual(self.listings.add.call_args.args[0].landlord_id, 8)
        self.db.commit.assert_called_once()

    def test_create_rejects_unknown_area(self) -> None:
        self.areas.get_by_id.return_value = None

        with self.assertRaises(ListingAreaNotFoundError):
            self.service.create_listing(8, self.create_request())

        self.listings.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_update_resets_submitted_listing_to_draft(self) -> None:
        listing = self.make_listing(status="pending")
        self.listings.get_owned.return_value = listing

        result = self.service.update_listing(
            8,
            12,
            ListingUpdateRequest(title="Updated room"),
        )

        self.assertEqual(result.title, "Updated room")
        self.assertEqual(result.status, "draft")
        self.db.commit.assert_called_once()

    def test_update_rejects_listing_not_owned_by_landlord(self) -> None:
        self.listings.get_owned.return_value = None

        with self.assertRaises(ListingNotFoundError):
            self.service.update_listing(
                8,
                12,
                ListingUpdateRequest(title="Updated room"),
            )

        self.db.commit.assert_not_called()

    def test_update_rejects_closed_listing(self) -> None:
        self.listings.get_owned.return_value = self.make_listing(status="closed")

        with self.assertRaises(ListingStateError):
            self.service.update_listing(
                8,
                12,
                ListingUpdateRequest(title="Updated room"),
            )

        self.db.commit.assert_not_called()

    def test_submit_moves_draft_to_pending(self) -> None:
        listing = self.make_listing()
        self.listings.get_owned.return_value = listing

        result = self.service.submit_listing(8, 12)

        self.assertEqual(result.status, "pending")
        self.db.commit.assert_called_once()

    def test_submit_is_idempotent_for_pending_listing(self) -> None:
        self.listings.get_owned.return_value = self.make_listing(
            status="pending",
        )

        result = self.service.submit_listing(8, 12)

        self.assertEqual(result.status, "pending")
        self.db.commit.assert_not_called()

    def test_submit_rejects_non_draft_listing(self) -> None:
        self.listings.get_owned.return_value = self.make_listing(
            status="active",
        )

        with self.assertRaises(ListingStateError):
            self.service.submit_listing(8, 12)

        self.db.commit.assert_not_called()

    def test_withdraw_moves_listing_to_closed(self) -> None:
        listing = self.make_listing(status="active")
        self.listings.get_owned.return_value = listing

        result = self.service.withdraw_listing(8, 12)

        self.assertEqual(result.status, "closed")
        self.db.commit.assert_called_once()

    def test_withdraw_is_idempotent_for_closed_listing(self) -> None:
        self.listings.get_owned.return_value = self.make_listing(
            status="closed",
        )

        result = self.service.withdraw_listing(8, 12)

        self.assertEqual(result.status, "closed")
        self.db.commit.assert_not_called()

    def test_photo_upload_resets_submitted_listing_to_draft(self) -> None:
        listing = self.make_listing(status="pending")
        self.listings.get_owned.return_value = listing
        self.photo_storage.upload.return_value = StoredPhoto(
            url="https://res.cloudinary.com/demo/image/upload/room.png",
            public_id="room-rental-platform/listings/room",
        )

        def add_photo(target: Listing, url: str) -> None:
            target.photos.append(
                ListingPhoto(
                    photo_id=5,
                    url=url,
                    uploaded_at=datetime(2026, 10, 1),
                )
            )

        self.listings.add_photo.side_effect = add_photo

        result = self.service.upload_photo(8, 12, BytesIO(b"image"))

        self.assertEqual(result.status, "draft")
        self.assertEqual(len(result.photos), 1)
        self.db.commit.assert_called_once()

    def test_photo_upload_cleans_up_cloudinary_asset_if_database_fails(
        self,
    ) -> None:
        self.listings.get_owned.return_value = self.make_listing()
        self.photo_storage.upload.return_value = StoredPhoto(
            url="https://res.cloudinary.com/demo/image/upload/room.png",
            public_id="room-rental-platform/listings/room",
        )
        self.db.commit.side_effect = SQLAlchemyError("database unavailable")

        with self.assertRaises(SQLAlchemyError):
            self.service.upload_photo(8, 12, BytesIO(b"image"))

        self.db.rollback.assert_called()
        self.photo_storage.delete.assert_called_once_with(
            "room-rental-platform/listings/room",
        )

    def test_closed_listing_cannot_receive_photo(self) -> None:
        self.listings.get_owned.return_value = self.make_listing(
            status="closed",
        )

        with self.assertRaises(ListingStateError):
            self.service.upload_photo(8, 12, BytesIO(b"image"))

        self.photo_storage.upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
