import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.services.role_service import (
    RoleConfigurationError,
    RoleService,
    UserNotFoundError,
)


class RoleServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = RoleService(self.db)
        self.service._users = Mock()
        self.service._roles = Mock()
        self.service._users.get_by_id.return_value = object()
        self.service._roles.get_by_name.return_value = SimpleNamespace(
            role_id=5,
            name="landlord",
        )
        self.service._roles.list_for_user.return_value = [
            SimpleNamespace(name="tenant"),
        ]

    def test_grant_adds_landlord_without_removing_existing_roles(self) -> None:
        with patch("app.services.role_service.logger") as logger:
            granted = self.service.grant_landlord_role(
                target_user_id=23,
                granted_by_user_id=4,
            )

        self.assertTrue(granted)
        self.service._roles.assign_to_user.assert_called_once_with(23, 5)
        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()
        logger.info.assert_called_once_with(
            "Granted landlord role",
            extra={
                "granted_by_user_id": 4,
                "target_user_id": 23,
            },
        )

    def test_grant_is_idempotent_when_role_already_exists(self) -> None:
        self.service._roles.list_for_user.return_value = [
            SimpleNamespace(name="tenant"),
            SimpleNamespace(name="landlord"),
        ]

        granted = self.service.grant_landlord_role(23, 4)

        self.assertFalse(granted)
        self.service._roles.assign_to_user.assert_not_called()
        self.db.commit.assert_not_called()

    def test_grant_rejects_unknown_user(self) -> None:
        self.service._users.get_by_id.return_value = None

        with self.assertRaises(UserNotFoundError):
            self.service.grant_landlord_role(999, 4)

        self.service._roles.get_by_name.assert_not_called()
        self.db.commit.assert_not_called()

    def test_grant_rolls_back_if_landlord_role_is_missing(self) -> None:
        self.service._roles.get_by_name.return_value = None

        with self.assertRaises(RoleConfigurationError):
            self.service.grant_landlord_role(23, 4)

        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_concurrent_duplicate_grant_is_idempotent(self) -> None:
        self.service._roles.assign_to_user.side_effect = IntegrityError(
            "insert",
            {},
            SimpleNamespace(
                diag=SimpleNamespace(constraint_name="user_roles_pkey"),
            ),
        )
        self.service._roles.list_for_user.side_effect = [
            [SimpleNamespace(name="tenant")],
            [
                SimpleNamespace(name="tenant"),
                SimpleNamespace(name="landlord"),
            ],
        ]

        granted = self.service.grant_landlord_role(23, 4)

        self.assertFalse(granted)
        self.db.rollback.assert_called_once()

    def test_other_database_errors_are_rolled_back_and_raised(self) -> None:
        self.service._roles.assign_to_user.side_effect = SQLAlchemyError(
            "database unavailable",
        )

        with self.assertRaises(SQLAlchemyError):
            self.service.grant_landlord_role(23, 4)

        self.db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
