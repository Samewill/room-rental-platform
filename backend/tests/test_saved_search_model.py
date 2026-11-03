import unittest

from sqlalchemy import CheckConstraint

from app.models.saved_search import SavedSearch


class SavedSearchModelTests(unittest.TestCase):
    def test_table_has_expected_columns(self) -> None:
        self.assertEqual(
            set(SavedSearch.__table__.columns.keys()),
            {
                "saved_search_id",
                "tenant_id",
                "location",
                "room_type",
                "minimum_rent",
                "maximum_rent",
                "created_at",
            },
        )

    def test_tenant_foreign_key_cascades_on_delete(self) -> None:
        tenant_id = SavedSearch.__table__.c.tenant_id
        foreign_key = next(iter(tenant_id.foreign_keys))

        self.assertEqual(foreign_key.target_fullname, "users.user_id")
        self.assertEqual(foreign_key.ondelete, "CASCADE")

    def test_rent_range_constraints_are_present(self) -> None:
        constraints = {
            constraint.name: str(constraint.sqltext)
            for constraint in SavedSearch.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }

        self.assertEqual(
            constraints,
            {
                "saved_searches_minimum_rent_check":
                    "minimum_rent IS NULL OR minimum_rent >= 0",
                "saved_searches_maximum_rent_check":
                    "maximum_rent IS NULL OR maximum_rent >= 0",
                "saved_searches_rent_range_check":
                    "minimum_rent IS NULL OR maximum_rent IS NULL "
                    "OR minimum_rent <= maximum_rent",
            },
        )

    def test_room_type_uses_existing_enum(self) -> None:
        room_type = SavedSearch.__table__.c.room_type

        self.assertEqual(room_type.type.name, "room_type_enum")
        self.assertFalse(room_type.type.create_type)


if __name__ == "__main__":
    unittest.main()
