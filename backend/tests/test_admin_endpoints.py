import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.admin import router
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.services.role_service import RoleService, UserNotFoundError


class AdminRoleEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.app.dependency_overrides[get_db] = lambda: Mock()
        self.admin = User(user_id=4)
        self.app.dependency_overrides[get_current_user] = lambda: self.admin
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

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
