import unittest

from sqlalchemy import CheckConstraint

from app.models.contact_request import ContactRequest


class ContactRequestModelTests(unittest.TestCase):
    def test_table_has_expected_columns(self) -> None:
        self.assertEqual(
            set(ContactRequest.__table__.columns.keys()),
            {
                "request_id",
                "listing_id",
                "tenant_id",
                "status",
                "requested_at",
            },
        )

    def test_foreign_keys_reference_listing_and_tenant(self) -> None:
        foreign_keys = {
            foreign_key.target_fullname
            for column in ContactRequest.__table__.columns
            for foreign_key in column.foreign_keys
        }

        self.assertEqual(
            foreign_keys,
            {"listings.listing_id", "users.user_id"},
        )

    def test_status_defaults_to_pending_and_has_known_values(self) -> None:
        status = ContactRequest.__table__.c.status
        self.assertEqual(status.server_default.arg, "pending")

        status_constraint = next(
            constraint
            for constraint in ContactRequest.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        )
        self.assertEqual(
            str(status_constraint.sqltext),
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
        )


if __name__ == "__main__":
    unittest.main()
