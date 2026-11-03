import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.router import api_router
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.services.auth_service import AccountAlreadyExistsError, AuthService
from app.services.user_service import UserService


class AuthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.app.dependency_overrides[get_db] = lambda: Mock()
        self.client = TestClient(self.app)
        self.user = User(
            user_id=42,
            full_name="Test User",
            phone_no="+27123456789",
            email="test.user@example.com",
            password_hash="not-returned",
            business_name=None,
            created_at=datetime.now(timezone.utc),
        )

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_registration_returns_safe_profile_with_selected_role(self) -> None:
        with patch.object(AuthService, "register", return_value=self.user) as register:
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test User",
                    "phone_no": "+27123456789",
                    "email": "test.user@example.com",
                    "password": "SecurePassword123",
                    "role": "landlord",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["roles"], ["landlord"])
        self.assertNotIn("password_hash", response.json())
        register.assert_called_once()
        self.assertEqual(register.call_args.args[0].role, "landlord")

    def test_registration_rejects_admin_self_registration(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test Admin",
                "phone_no": "+27123456789",
                "email": "admin@example.com",
                "password": "SecurePassword123",
                "role": "admin",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_tenant_registration_rejects_business_name(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test Tenant",
                "phone_no": "+27123456789",
                "email": "tenant@example.com",
                "password": "SecurePassword123",
                "role": "tenant",
                "business_name": "Not for tenants",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_registration_returns_conflict_for_existing_account(self) -> None:
        with patch.object(
            AuthService,
            "register",
            side_effect=AccountAlreadyExistsError(
                "An account with these details already exists.",
            ),
        ):
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test User",
                    "phone_no": "+27123456789",
                    "email": "test.user@example.com",
                    "password": "SecurePassword123",
                    "role": "tenant",
                },
            )

        self.assertEqual(response.status_code, 409)

    def test_login_returns_bearer_token_and_expiry(self) -> None:
        with (
            patch.object(AuthService, "authenticate", return_value=self.user),
            patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="test-access-token",
            ),
            patch(
                "app.api.v1.endpoints.auth.get_settings",
                return_value=Mock(access_token_expire_minutes=30),
            ),
        ):
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test.user@example.com",
                    "password": "SecurePassword123",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "test-access-token",
                "token_type": "bearer",
                "expires_in": 1800,
            },
        )

    def test_login_rejects_invalid_credentials(self) -> None:
        with patch.object(AuthService, "authenticate", return_value=None):
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test.user@example.com",
                    "password": "WrongPassword123",
                },
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers["www-authenticate"],
            "Bearer",
        )

    def test_profile_requires_authentication(self) -> None:
        response = self.client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 401)

    def test_profile_returns_roles_without_password_hash(self) -> None:
        self.app.dependency_overrides[get_current_user] = lambda: self.user

        with patch.object(
            RoleRepository,
            "list_for_user",
            return_value=[Role(role_id=3, name="tenant")],
        ):
            response = self.client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["roles"], ["tenant"])
        self.assertNotIn("password_hash", response.json())

    def test_profile_update_allows_name_fields_but_rejects_email(self) -> None:
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        updated_user = User(
            user_id=42,
            full_name="Updated Name",
            phone_no="+27123456789",
            email="test.user@example.com",
            password_hash="not-returned",
            business_name="Updated Business",
            created_at=self.user.created_at,
        )

        with (
            patch.object(UserService, "update_profile", return_value=updated_user),
            patch.object(
                RoleRepository,
                "list_for_user",
                return_value=[Role(role_id=3, name="tenant")],
            ),
        ):
            response = self.client.patch(
                "/api/v1/users/me",
                json={
                    "full_name": "Updated Name",
                    "business_name": "Updated Business",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["full_name"], "Updated Name")
        self.assertEqual(
            response.json()["business_name"],
            "Updated Business",
        )
        self.assertEqual(response.json()["roles"], ["tenant"])
        self.assertNotIn("password_hash", response.json())

        invalid_response = self.client.patch(
            "/api/v1/users/me",
            json={"email": "new@example.com"},
        )
        self.assertEqual(invalid_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
