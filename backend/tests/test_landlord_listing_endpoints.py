import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.landlord_listings import (
    get_landlord_listing_service,
    landlord_dependency,
)
from app.api.v1.router import api_router
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.listing import ListingResponse


class LandlordListingEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.landlord = User(user_id=8)
        self.app.dependency_overrides[get_landlord_listing_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[landlord_dependency] = (
            lambda: self.landlord
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_listing(
        listing_id: int = 12,
        status: str = "draft",
    ) -> ListingResponse:
        return ListingResponse(
            listing_id=listing_id,
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
            photos=[],
        )

    def test_list_my_listings_uses_authenticated_landlord_id(self) -> None:
        self.service.list_for_landlord.return_value = [
            self.make_listing(),
        ]

        response = self.client.get("/api/v1/users/me/listings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["listing_id"], 12)
        self.service.list_for_landlord.assert_called_once_with(8)

    def test_create_listing_uses_authenticated_landlord_id(self) -> None:
        self.service.create_listing.return_value = self.make_listing()

        response = self.client.post(
            "/api/v1/listings",
            json={
                "area_id": 3,
                "title": "A room",
                "description": "A room description",
                "room_type": "single_room",
                "monthly_rent": "4200.00",
                "deposit_amount": "4200.00",
                "address": "Test address",
                "date_available": "2026-11-01",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "draft")
        self.assertEqual(self.service.create_listing.call_args.args[0], 8)

    def test_create_listing_rejects_client_supplied_owner(self) -> None:
        response = self.client.post(
            "/api/v1/listings",
            json={
                "landlord_id": 99,
                "area_id": 3,
                "title": "A room",
                "description": "A room description",
                "room_type": "single_room",
                "monthly_rent": "4200.00",
                "deposit_amount": "4200.00",
                "address": "Test address",
                "date_available": "2026-11-01",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_listing.assert_not_called()

    def test_update_listing_calls_service_with_authenticated_owner(self) -> None:
        self.service.update_listing.return_value = self.make_listing()

        response = self.client.patch(
            "/api/v1/listings/12",
            json={"title": "Updated room"},
        )

        self.assertEqual(response.status_code, 200)
        self.service.update_listing.assert_called_once()
        self.assertEqual(self.service.update_listing.call_args.args[:2], (8, 12))

    def test_submit_listing_calls_service_with_authenticated_owner(self) -> None:
        self.service.submit_listing.return_value = self.make_listing(
            status="pending",
        )

        response = self.client.post("/api/v1/listings/12/submit")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        self.service.submit_listing.assert_called_once_with(8, 12)

    def test_withdraw_listing_calls_service_with_authenticated_owner(
        self,
    ) -> None:
        self.service.withdraw_listing.return_value = self.make_listing(
            status="closed",
        )

        response = self.client.post("/api/v1/listings/12/withdraw")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "closed")
        self.service.withdraw_listing.assert_called_once_with(8, 12)

    def test_upload_photo_passes_image_to_service(self) -> None:
        self.service.upload_photo.return_value = self.make_listing()

        response = self.client.post(
            "/api/v1/listings/12/photos",
            files={"photo": ("room.png", b"test image", "image/png")},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.service.upload_photo.call_args.args[:2], (8, 12))

    def test_upload_photo_rejects_unsupported_media_type(self) -> None:
        response = self.client.post(
            "/api/v1/listings/12/photos",
            files={"photo": ("room.gif", b"test image", "image/gif")},
        )

        self.assertEqual(response.status_code, 415)
        self.service.upload_photo.assert_not_called()

    def test_landlord_routes_reject_missing_authentication(self) -> None:
        self.app.dependency_overrides.pop(landlord_dependency)
        self.app.dependency_overrides[get_db] = lambda: Mock()

        response = self.client.get("/api/v1/users/me/listings")

        self.assertEqual(response.status_code, 401)
        self.service.list_for_landlord.assert_not_called()

    def test_tenant_cannot_use_landlord_listing_routes(self) -> None:
        self.app.dependency_overrides.pop(landlord_dependency)
        self.app.dependency_overrides[get_current_user] = lambda: User(
            user_id=9,
        )
        self.app.dependency_overrides[get_db] = lambda: Mock()
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="tenant"),
        ]

        with patch(
            "app.api.dependencies.RoleRepository",
            return_value=role_repository,
        ):
            response = self.client.get("/api/v1/users/me/listings")

        self.assertEqual(response.status_code, 403)
        self.service.list_for_landlord.assert_not_called()


if __name__ == "__main__":
    unittest.main()
