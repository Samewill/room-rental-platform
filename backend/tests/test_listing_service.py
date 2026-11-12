import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.listing_service import ListingService


class ListingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = Mock()
        self.google_places = Mock()
        self.service = ListingService(self.repository, self.google_places)

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
            latitude=None,
            longitude=None,
            google_place_id=None,
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

    def test_radius_search_uses_stored_coordinates_without_exposing_them(
        self,
    ) -> None:
        nearby = self.make_listing(1)
        nearby.latitude = -29.04
        nearby.longitude = 24
        outside = self.make_listing(2)
        outside.latitude = -29.06
        outside.longitude = 24
        self.repository.list_all.return_value = [nearby, outside]
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
            2: "approved",
        }

        result = self.service.list_public_listings(
            center=(-29, 24),
            radius_km=5,
        )

        self.assertEqual([listing.listing_id for listing in result], [1])
        self.assertEqual(result[0].approximate_latitude, -29.04)
        self.assertFalse(hasattr(result[0], "latitude"))
        self.google_places.get_location.assert_not_called()

    def test_radius_search_resolves_place_ids_and_includes_nearby_places(
        self,
    ) -> None:
        listing = self.make_listing(1)
        listing.google_place_id = "google-place-id"
        self.repository.list_all.return_value = [listing]
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }
        self.google_places.get_location.return_value = (-29.04, 24)

        result = self.service.list_public_listings(
            center=(-29, 24),
            radius_km=5,
        )

        self.assertEqual([item.listing_id for item in result], [1])
        self.assertEqual(result[0].approximate_latitude, -29.04)
        self.assertFalse(hasattr(result[0], "google_place_id"))
        self.assertFalse(hasattr(result[0], "latitude"))
        self.assertFalse(hasattr(result[0], "longitude"))
        self.google_places.get_location.assert_called_once_with(
            "google-place-id",
        )

    def test_radius_search_excludes_listings_without_any_map_location(
        self,
    ) -> None:
        listing = self.make_listing(1)
        self.repository.list_all.return_value = [listing]
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.list_public_listings(
            center=(-29, 24),
            radius_km=10,
        )

        self.assertEqual(result, [])
        self.google_places.get_location.assert_not_called()

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

    def test_public_coordinates_are_rounded_before_response(self) -> None:
        listing = self.make_listing(1)
        listing.latitude = -26.204167
        listing.longitude = 28.047305
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.get_public_listing(1)

        self.assertIsNotNone(result)
        self.assertEqual(result.approximate_latitude, -26.2)
        self.assertEqual(result.approximate_longitude, 28.05)
        self.assertFalse(hasattr(result, "latitude"))
        self.assertFalse(hasattr(result, "longitude"))

    def test_public_response_without_coordinates_has_no_map_location(
        self,
    ) -> None:
        listing = self.make_listing(1)
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.get_public_listing(1)

        self.assertFalse(result.has_map_location)
        self.assertIsNone(result.approximate_latitude)
        self.assertIsNone(result.approximate_longitude)

    def test_google_place_location_is_resolved_and_rounded_on_demand(self) -> None:
        listing = self.make_listing(1)
        listing.google_place_id = "google-place-id"
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }
        self.google_places.get_location.return_value = (
            -26.204167,
            28.047305,
        )

        result = self.service.get_public_listing_location(1)

        self.assertEqual(result.approximate_latitude, -26.2)
        self.assertEqual(result.approximate_longitude, 28.05)
        self.google_places.get_location.assert_called_once_with(
            "google-place-id",
        )
        self.assertIsNone(listing.latitude)
        self.assertIsNone(listing.longitude)

    def test_google_place_location_is_not_resolved_for_unapproved_listing(
        self,
    ) -> None:
        listing = self.make_listing(1)
        listing.google_place_id = "google-place-id"
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "rejected",
        }

        self.assertIsNone(self.service.get_public_listing_location(1))
        self.google_places.get_location.assert_not_called()

    def test_public_listing_signals_google_map_without_exposing_place_id(
        self,
    ) -> None:
        listing = self.make_listing(1)
        listing.google_place_id = "google-place-id"
        self.repository.get_by_id.return_value = listing
        self.repository.get_latest_moderation_decisions.return_value = {
            1: "approved",
        }

        result = self.service.get_public_listing(1)

        self.assertTrue(result.has_map_location)
        self.assertFalse(hasattr(result, "google_place_id"))
        self.assertIsNone(result.approximate_latitude)

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
