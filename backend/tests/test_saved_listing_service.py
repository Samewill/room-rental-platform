import unittest
from unittest.mock import Mock

from sqlalchemy.exc import IntegrityError

from app.models.saved_listing import SavedListing
from app.services.saved_listing_service import (
    SavedListingService,
    SavedListingUnavailableError,
)


class SavedListingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = SavedListingService(self.db)
        self.service._listings = Mock()
        self.service._saved_listings = Mock()

    def test_saving_unavailable_listing_is_rejected(self) -> None:
        self.service._listings.get_public_listing.return_value = None

        with self.assertRaises(SavedListingUnavailableError):
            self.service.save_for_tenant(tenant_id=6, listing_id=12)

        self.service._saved_listings.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_saving_public_listing_is_idempotent(self) -> None:
        self.service._listings.get_public_listing.return_value = Mock()
        self.service._saved_listings.get_for_tenant.return_value = SavedListing(
            tenant_id=6,
            listing_id=12,
        )

        self.assertFalse(self.service.save_for_tenant(6, 12))

        self.service._saved_listings.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_unique_race_is_idempotent_for_same_tenant_listing(self) -> None:
        self.service._listings.get_public_listing.return_value = Mock()
        self.service._saved_listings.get_for_tenant.side_effect = [
            None,
            SavedListing(tenant_id=6, listing_id=12),
        ]
        self.db.commit.side_effect = IntegrityError(
            "duplicate",
            {},
            Exception("duplicate"),
        )

        self.assertFalse(self.service.save_for_tenant(6, 12))

        self.db.rollback.assert_called_once()

    def test_listing_for_another_tenant_does_not_make_save_idempotent(
        self,
    ) -> None:
        self.service._listings.get_public_listing.return_value = Mock()
        self.service._saved_listings.get_for_tenant.side_effect = [None, None]
        self.db.commit.side_effect = IntegrityError(
            "foreign key failure",
            {},
            Exception("foreign key failure"),
        )

        with self.assertRaises(IntegrityError):
            self.service.save_for_tenant(6, 12)


if __name__ == "__main__":
    unittest.main()
