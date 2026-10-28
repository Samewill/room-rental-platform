from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from sqlalchemy.exc import IntegrityError

from app.models.role import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    AccountAlreadyExistsError,
    AuthService,
    RoleConfigurationError,
)


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = AuthService(self.db)
        self.service._users = Mock()
        self.service._roles = Mock()
        self.service._users.get_by_email.return_value = None
        self.service._users.get_by_phone_no.return_value = None
        self.service._roles.get_by_name.return_value = Role(
            role_id=3,
            name="tenant",
        )
        self.registration = RegisterRequest(
            full_name="Test User",
            phone_no="+27123456789",
            email="Test.User@example.com",
            password="SecurePassword123",
            role="tenant",
        )

    def test_register_hashes_password_assigns_tenant_and_commits(self) -> None:
        def add_user(user: User) -> User:
            user.user_id = 42
            return user

        self.service._users.add.side_effect = add_user

        with patch(
            "app.services.auth_service.hash_password",
            return_value="argon2-hash",
        ) as hash_password:
            user = self.service.register(self.registration)

        self.assertEqual(user.email, "test.user@example.com")
        self.assertEqual(user.password_hash, "argon2-hash")
        hash_password.assert_called_once_with("SecurePassword123")
        self.service._roles.get_by_name.assert_called_once_with("tenant")
        self.service._roles.assign_to_user.assert_called_once_with(42, 3)
        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()

    def test_register_assigns_selected_landlord_role(self) -> None:
        def add_user(user: User) -> User:
            user.user_id = 43
            return user

        self.service._users.add.side_effect = add_user
        self.service._roles.get_by_name.return_value = Role(
            role_id=4,
            name="landlord",
        )

        with patch(
            "app.services.auth_service.hash_password",
            return_value="argon2-hash",
        ):
            self.service.register(
                self.registration.model_copy(update={"role": "landlord"}),
            )

        self.service._roles.get_by_name.assert_called_once_with("landlord")
        self.service._roles.assign_to_user.assert_called_once_with(43, 4)
        self.db.commit.assert_called_once()

    def test_register_rejects_existing_email(self) -> None:
        self.service._users.get_by_email.return_value = User(user_id=7)

        with self.assertRaises(AccountAlreadyExistsError):
            self.service.register(self.registration)

        self.service._roles.get_by_name.assert_not_called()
        self.service._users.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_register_rejects_existing_phone_number(self) -> None:
        self.service._users.get_by_phone_no.return_value = User(user_id=7)

        with self.assertRaises(AccountAlreadyExistsError):
            self.service.register(self.registration)

        self.service._roles.get_by_name.assert_not_called()
        self.service._users.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_register_rolls_back_if_selected_role_is_missing(self) -> None:
        self.service._roles.get_by_name.return_value = None

        with self.assertRaises(RoleConfigurationError):
            self.service.register(self.registration)

        self.service._roles.get_by_name.assert_called_once_with("tenant")
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()
        self.service._users.add.assert_not_called()

    def test_register_translates_concurrent_duplicate_email(self) -> None:
        def add_user(user: User) -> User:
            user.user_id = 42
            return user

        self.service._users.add.side_effect = add_user
        self.db.commit.side_effect = IntegrityError(
            "insert",
            {},
            SimpleNamespace(
                diag=SimpleNamespace(constraint_name="users_email_key"),
            ),
        )

        with (
            patch(
                "app.services.auth_service.hash_password",
                return_value="argon2-hash",
            ),
            self.assertRaises(AccountAlreadyExistsError),
        ):
            self.service.register(self.registration)

        self.db.rollback.assert_called_once()

    def test_authenticate_uses_casefolded_email_and_verifies_password(self) -> None:
        user = User(user_id=42, password_hash="argon2-hash")
        self.service._users.get_by_email.return_value = user

        with patch(
            "app.services.auth_service.verify_password",
            return_value=True,
        ) as verify_password:
            result = self.service.authenticate(
                LoginRequest(
                    email="Test.User@example.com",
                    password="SecurePassword123",
                )
            )

        self.assertIs(result, user)
        self.service._users.get_by_email.assert_called_once_with(
            "test.user@example.com",
        )
        verify_password.assert_called_once_with(
            "SecurePassword123",
            "argon2-hash",
        )

    def test_authenticate_rejects_wrong_password(self) -> None:
        self.service._users.get_by_email.return_value = User(
            user_id=42,
            password_hash="argon2-hash",
        )

        with patch(
            "app.services.auth_service.verify_password",
            return_value=False,
        ):
            result = self.service.authenticate(
                LoginRequest(
                    email="test.user@example.com",
                    password="WrongPassword123",
                )
            )

        self.assertIsNone(result)

    def test_authenticate_rejects_user_without_password_hash(self) -> None:
        self.service._users.get_by_email.return_value = User(
            user_id=42,
            password_hash=None,
        )

        with patch(
            "app.services.auth_service.verify_password",
        ) as verify_password:
            result = self.service.authenticate(
                LoginRequest(
                    email="test.user@example.com",
                    password="SecurePassword123",
                )
            )

        self.assertIsNone(result)
        verify_password.assert_not_called()


if __name__ == "__main__":
    unittest.main()
