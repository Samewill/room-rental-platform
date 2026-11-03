import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.listing_service import ListingService


class ListingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = Mock()
        self.service = ListingService(self.repository)

    @staticmethod
    def make_listing(
        listing_id: int,
        *,
        status: str = "active",
        date_available: date = date(2026, 10, 28),
    ) -> SimpleNamespace:
        return SimpleNamespace(
            listing_id=listing_id,
            area_id=3,
            title=f"Room {listing_id}",
            description="A test room.",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date_available,
            status=status,
            created_at=datetime(2026, 10, 1),
            photos=[],
        )

    def test_list_returns_active_approved_listings_with_future_availability(
        self,
    ) -> None:
        approved = self.make_listing(1)
        pending_approval = self.make_listing(2)
        future = self.make_listing(
            3,
            date_available=date(2026, 10, 29),
        )
        withdrawn = self.make_listing(4, status="withdrawn")
        self.repository.list_all.return_value = [
            approved,
            pending_approval,
            future,
            withdrawn,
        ]
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
            2: "pending",
            3: "approved",
            4: "approved",
        }

        result = self.service.list_public_listings()

        self.assertEqual([listing.listing_id for listing in result], [1, 3])
        self.repository.get_latest_moderation_decisions.assert_called_once_with(
            [1, 2, 3],
        )

    def test_list_excludes_listings_without_moderation_decisions(self) -> None:
        listing = self.make_listing(1)
        self.repository.list_all.return_value = [listing]
        self.repository.get_latest_moderation_decisions.return_value = {}

        result = self.service.list_public_listings()

        self.assertEqual(result, [])

    def test_list_passes_no_candidates_when_no_listings_are_active(
        self,
    ) -> None:
        inactive = self.make_listing(1, status="draft")
        self.repository.list_all.return_value = [inactive]

        result = self.service.list_public_listings()

        self.assertEqual(result, [])
        self.repository.get_latest_moderation_decisions.assert_called_once_with(
            [],
        )

    def test_get_returns_approved_listing_with_future_availability(self) -> None:
        listing = self.make_listing(
            1,
            date_available=date(2026, 10, 29),
        )
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.get_public_listing(1)

        self.assertIsNotNone(result)
        self.assertEqual(result.listing_id, 1)

    def test_get_returns_approved_listing(self) -> None:
        listing = self.make_listing(1)
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.get_public_listing(1)

        self.assertIsNotNone(result)
        self.assertEqual(result.listing_id, 1)

    def test_get_excludes_unapproved_listing(self) -> None:
        listing = self.make_listing(1)
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "rejected",
        }

        result = self.service.get_public_listing(1)

        self.assertIsNone(result)

    def test_get_returns_none_for_missing_listing(self) -> None:
        self.repository.get_by_id.return_value = None

        result = self.service.get_public_listing(999)

        self.assertIsNone(result)
        self.repository.get_latest_moderation_decisions.assert_not_called()


if __name__ == "__main__":
    unittest.main()
