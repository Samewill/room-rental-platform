import unittest
from unittest.mock import Mock

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.schemas.user import UserProfileUpdate
from app.services.user_service import UserService


class UserServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = UserService(self.db)
        self.user = User(
            user_id=42,
            full_name="Original Name",
            phone_no="+27123456789",
            email="user@example.com",
            business_name="Original Business",
        )

    def test_update_profile_changes_only_supplied_fields(self) -> None:
        result = self.service.update_profile(
            self.user,
            UserProfileUpdate(full_name=" Updated Name "),
        )

        self.assertIs(result, self.user)
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.business_name, "Original Business")
        self.assertEqual(self.user.email, "user@example.com")
        self.assertEqual(self.user.phone_no, "+27123456789")
        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()

    def test_update_profile_can_clear_business_name(self) -> None:
        result = self.service.update_profile(
            self.user,
            UserProfileUpdate(business_name=None),
        )

        self.assertIs(result, self.user)
        self.assertIsNone(self.user.business_name)
        self.assertEqual(self.user.full_name, "Original Name")
        self.db.commit.assert_called_once()

    def test_update_profile_rolls_back_and_surfaces_database_error(self) -> None:
        self.db.commit.side_effect = SQLAlchemyError("database unavailable")

        with self.assertRaises(SQLAlchemyError):
            self.service.update_profile(
                self.user,
                UserProfileUpdate(full_name="Updated Name"),
            )

        self.db.commit.assert_called_once()
        self.db.rollback.assert_called_once()

    def test_profile_update_schema_rejects_empty_update(self) -> None:
        with self.assertRaises(ValidationError):
            UserProfileUpdate()

    def test_profile_update_schema_rejects_email_and_phone_changes(self) -> None:
        for field_name, value in (
            ("email", "new@example.com"),
            ("phone_no", "+27119999999"),
        ):
            with self.subTest(field=field_name):
                with self.assertRaises(ValidationError):
                    UserProfileUpdate(**{field_name: value})

    def test_profile_update_schema_requires_nonblank_name(self) -> None:
        for value in (None, "", "   "):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    UserProfileUpdate(full_name=value)


if __name__ == "__main__":
    unittest.main()
