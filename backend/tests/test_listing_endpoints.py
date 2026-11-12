import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints.listings import get_listing_service
from app.api.v1.router import api_router
from app.schemas.listing import ListingResponse
from app.schemas.location import PublicListingLocationResponse
from app.services.google_places import (
    GooglePlacesConfigurationError,
    GooglePlacesError,
    GooglePlacesLookupError,
)


class ListingEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.app.dependency_overrides[get_listing_service] = (
            lambda: self.service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_listing(listing_id: int = 1) -> ListingResponse:
        return ListingResponse(
            listing_id=listing_id,
            area_id=3,
            title=f"Room {listing_id}",
            description="A test room.",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date(2026, 10, 28),
            status="active",
            created_at=datetime(2026, 10, 1),
            photos=[],
        )

    def test_list_public_listings_returns_service_results(self) -> None:
        self.service.list_public_listings.return_value = [
            self.make_listing(1),
            self.make_listing(2),
        ]

        response = self.client.get("/api/v1/listings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [listing["listing_id"] for listing in response.json()],
            [1, 2],
        )
        self.service.list_public_listings.assert_called_once_with()

    def test_list_public_listings_passes_complete_radius_filter(self) -> None:
        self.service.list_public_listings.return_value = [self.make_listing(2)]

        response = self.client.get(
            "/api/v1/listings",
            params={
                "latitude": "-26.2",
                "longitude": "28.05",
                "radius_km": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.service.list_public_listings.assert_called_once_with(
            center=(-26.2, 28.05),
            radius_km=10,
        )

    def test_list_public_listings_rejects_partial_radius_filter(self) -> None:
        response = self.client.get(
            "/api/v1/listings",
            params={"latitude": "-26.2", "radius_km": "5"},
        )

        self.assertEqual(response.status_code, 422)
        self.service.list_public_listings.assert_not_called()

    def test_list_public_listings_returns_unavailable_on_place_lookup_error(
        self,
    ) -> None:
        self.service.list_public_listings.side_effect = GooglePlacesError(
            "provider unavailable",
        )

        response = self.client.get(
            "/api/v1/listings",
            params={
                "latitude": "-26.2",
                "longitude": "28.05",
                "radius_km": "5",
            },
        )

        self.assertEqual(response.status_code, 503)

    def test_list_public_listings_returns_service_unavailable_on_database_error(
        self,
    ) -> None:
        self.service.list_public_listings.side_effect = SQLAlchemyError(
            "database unavailable",
        )

        response = self.client.get("/api/v1/listings")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Listing data is temporarily unavailable.",
        )

    def test_get_public_listing_returns_service_result(self) -> None:
        self.service.get_public_listing.return_value = self.make_listing(7)

        response = self.client.get("/api/v1/listings/7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["listing_id"], 7)
        self.service.get_public_listing.assert_called_once_with(7)

    def test_get_public_listing_returns_not_found_when_missing(self) -> None:
        self.service.get_public_listing.return_value = None

        response = self.client.get("/api/v1/listings/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Listing not found.")

    def test_get_public_listing_rejects_non_positive_id(self) -> None:
        response = self.client.get("/api/v1/listings/0")

        self.assertEqual(response.status_code, 422)
        self.service.get_public_listing.assert_not_called()

    def test_get_public_listing_returns_service_unavailable_on_database_error(
        self,
    ) -> None:
        self.service.get_public_listing.side_effect = SQLAlchemyError(
            "database unavailable",
        )

        response = self.client.get("/api/v1/listings/7")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Listing data is temporarily unavailable.",
        )

    def test_get_public_map_location_returns_service_result(self) -> None:
        self.service.get_public_listing_location.return_value = (
            PublicListingLocationResponse(
                approximate_latitude=-26.2,
                approximate_longitude=28.05,
            )
        )

        response = self.client.get("/api/v1/listings/7/map-location")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "approximate_latitude": -26.2,
                "approximate_longitude": 28.05,
            },
        )
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.service.get_public_listing_location.assert_called_once_with(7)

    def test_get_public_map_location_returns_not_found_when_missing(
        self,
    ) -> None:
        self.service.get_public_listing_location.return_value = None

        response = self.client.get("/api/v1/listings/7/map-location")

        self.assertEqual(response.status_code, 404)

    def test_get_public_map_location_returns_unavailable_on_provider_error(
        self,
    ) -> None:
        self.service.get_public_listing_location.side_effect = (
            GooglePlacesLookupError("provider unavailable")
        )

        response = self.client.get("/api/v1/listings/7/map-location")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Map location is temporarily unavailable.",
        )

    def test_get_public_map_location_returns_unavailable_without_key(
        self,
    ) -> None:
        self.service.get_public_listing_location.side_effect = (
            GooglePlacesConfigurationError("missing key")
        )

        response = self.client.get("/api/v1/listings/7/map-location")

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
