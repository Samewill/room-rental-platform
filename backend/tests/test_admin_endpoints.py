import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.admin import (
    admin_dependency,
    get_listing_moderation_service,
    router,
)
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.listing import ListingResponse
from app.schemas.listing_moderation import ListingModerationResponse
from app.services.role_service import RoleService, UserNotFoundError
from app.services.listing_moderation_service import (
    ModerationListingNotFoundError,
    ModerationStateError,
)


class AdminRoleEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.app.dependency_overrides[get_db] = lambda: Mock()
        self.admin = User(user_id=4)
        self.app.dependency_overrides[get_current_user] = lambda: self.admin
        self.app.dependency_overrides[admin_dependency] = lambda: self.admin
        self.moderation_service = Mock()
        self.app.dependency_overrides[get_listing_moderation_service] = (
            lambda: self.moderation_service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_listing(status: str = "pending") -> ListingResponse:
        return ListingResponse(
            listing_id=12,
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

    @staticmethod
    def make_moderation() -> ListingModerationResponse:
        return ListingModerationResponse(
            moderation_id=2,
            listing_id=12,
            admin_id=4,
            decision="rejected",
            reason="Missing details",
            decided_at=datetime(2026, 10, 2),
        )

    def test_admin_can_list_pending_listings(self) -> None:
        self.moderation_service.list_pending_listings.return_value = [
            self.make_listing(),
        ]

        response = self.client.get("/api/v1/admin/listings/pending")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["listing_id"], 12)

    def test_admin_can_list_published_listings(self) -> None:
        self.moderation_service.list_published_listings.return_value = [
            self.make_listing(status="active"),
        ]

        response = self.client.get("/api/v1/admin/listings/published")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["status"], "active")

    def test_admin_can_read_listing_moderation_history(self) -> None:
        self.moderation_service.get_moderation_history.return_value = [
            self.make_moderation(),
        ]

        response = self.client.get(
            "/api/v1/admin/listings/12/moderation-history",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["decision"], "rejected")

    def test_approval_uses_authenticated_admin_id(self) -> None:
        self.moderation_service.approve_listing.return_value = self.make_listing(
            status="active",
        )

        response = self.client.post(
            "/api/v1/admin/listings/12/approve",
            json={"reason": "Meets requirements"},
        )

        self.assertEqual(response.status_code, 200)
        self.moderation_service.approve_listing.assert_called_once_with(
            12,
            4,
            "Meets requirements",
        )

    def test_rejection_uses_authenticated_admin_id_and_reason(self) -> None:
        self.moderation_service.reject_listing.return_value = self.make_listing(
            status="draft",
        )

        response = self.client.post(
            "/api/v1/admin/listings/12/reject",
            json={"reason": "Missing details"},
        )

        self.assertEqual(response.status_code, 200)
        self.moderation_service.reject_listing.assert_called_once_with(
            12,
            4,
            "Missing details",
        )

    def test_rejection_requires_a_nonblank_reason(self) -> None:
        response = self.client.post(
            "/api/v1/admin/listings/12/reject",
            json={"reason": "   "},
        )

        self.assertEqual(response.status_code, 422)
        self.moderation_service.reject_listing.assert_not_called()

    def test_hide_uses_authenticated_admin_id_and_reason(self) -> None:
        self.moderation_service.hide_listing.return_value = self.make_listing(
            status="removed",
        )

        response = self.client.post(
            "/api/v1/admin/listings/12/hide",
            json={"reason": "Policy violation"},
        )

        self.assertEqual(response.status_code, 200)
        self.moderation_service.hide_listing.assert_called_once_with(
            12,
            4,
            "Policy violation",
        )

    def test_moderation_state_conflict_maps_to_409(self) -> None:
        self.moderation_service.approve_listing.side_effect = (
            ModerationStateError("Only pending listings can be moderated.")
        )

        response = self.client.post("/api/v1/admin/listings/12/approve")

        self.assertEqual(response.status_code, 409)

    def test_missing_listing_history_maps_to_404(self) -> None:
        self.moderation_service.get_moderation_history.side_effect = (
            ModerationListingNotFoundError("Listing does not exist.")
        )

        response = self.client.get(
            "/api/v1/admin/listings/999/moderation-history",
        )

        self.assertEqual(response.status_code, 404)

    def test_database_error_maps_to_503(self) -> None:
        self.moderation_service.list_pending_listings.side_effect = (
            SQLAlchemyError("database unavailable")
        )

        response = self.client.get("/api/v1/admin/listings/pending")

        self.assertEqual(response.status_code, 503)

    def test_non_admin_cannot_access_moderation_queue(self) -> None:
        self.app.dependency_overrides.pop(admin_dependency)
        self.app.dependency_overrides[get_current_user] = lambda: User(
            user_id=5,
        )
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=2, name="tenant"),
        ]

        with patch(
            "app.api.dependencies.RoleRepository",
            return_value=role_repository,
        ):
            response = self.client.get("/api/v1/admin/listings/pending")

        self.assertEqual(response.status_code, 403)
        self.moderation_service.list_pending_listings.assert_not_called()

    def test_admin_can_grant_landlord_role_to_another_user(self) -> None:
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="admin"),
        ]
        role_service = Mock()
        role_service.grant_landlord_role.return_value = True

        with (
            patch(
                "app.api.dependencies.RoleRepository",
                return_value=role_repository,
            ),
            patch("app.api.v1.endpoints.admin.RoleService", return_value=role_service),
        ):
            response = self.client.post(
                "/api/v1/admin/users/23/roles/landlord",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_id": 23, "role": "landlord", "granted": True},
        )
        role_service.grant_landlord_role.assert_called_once_with(
            target_user_id=23,
            granted_by_user_id=4,
        )

    def test_repeat_grant_reports_no_change(self) -> None:
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="admin"),
        ]
        role_service = Mock()
        role_service.grant_landlord_role.return_value = False

        with (
            patch(
                "app.api.dependencies.RoleRepository",
                return_value=role_repository,
            ),
            patch("app.api.v1.endpoints.admin.RoleService", return_value=role_service),
        ):
            response = self.client.post(
                "/api/v1/admin/users/23/roles/landlord",
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["granted"])

    def test_non_admin_cannot_grant_landlord_role(self) -> None:
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=2, name="tenant"),
        ]

        with (
            patch(
                "app.api.dependencies.RoleRepository",
                return_value=role_repository,
            ),
            patch("app.api.v1.endpoints.admin.RoleService") as role_service,
        ):
            response = self.client.post(
                "/api/v1/admin/users/23/roles/landlord",
            )

        self.assertEqual(response.status_code, 403)
        role_service.assert_not_called()

    def test_admin_cannot_grant_landlord_role_to_themselves(self) -> None:
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="admin"),
        ]

        with (
            patch(
                "app.api.dependencies.RoleRepository",
                return_value=role_repository,
            ),
            patch("app.api.v1.endpoints.admin.RoleService") as role_service,
        ):
            response = self.client.post(
                "/api/v1/admin/users/4/roles/landlord",
            )

        self.assertEqual(response.status_code, 403)
        role_service.assert_not_called()

    def test_unknown_target_user_returns_not_found(self) -> None:
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="admin"),
        ]
        role_service = Mock()
        role_service.grant_landlord_role.side_effect = UserNotFoundError(
            "User does not exist.",
        )

        with (
            patch(
                "app.api.dependencies.RoleRepository",
                return_value=role_repository,
            ),
            patch("app.api.v1.endpoints.admin.RoleService", return_value=role_service),
        ):
            response = self.client.post(
                "/api/v1/admin/users/999/roles/landlord",
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
