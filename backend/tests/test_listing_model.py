import unittest

from sqlalchemy.dialects.postgresql import ENUM

from app.models.listing import Listing


class ListingModelTests(unittest.TestCase):
    def test_coordinates_are_optional_and_constrained_as_a_pair(self) -> None:
        self.assertTrue(Listing.__table__.c.latitude.nullable)
        self.assertTrue(Listing.__table__.c.longitude.nullable)
        self.assertTrue(Listing.__table__.c.google_place_id.nullable)
        constraint_names = {
            constraint.name
            for constraint in Listing.__table__.constraints
        }

        self.assertIn("listings_coordinates_pair_check", constraint_names)
        self.assertIn("listings_latitude_range_check", constraint_names)
        self.assertIn("listings_longitude_range_check", constraint_names)
        self.assertIn(
            "listings_google_place_coordinates_check",
            constraint_names,
        )

    def test_room_type_uses_existing_postgresql_enum(self) -> None:
        room_type = Listing.__table__.c.room_type.type

        self.assertIsInstance(room_type, ENUM)
        self.assertEqual(room_type.name, "room_type_enum")
        self.assertEqual(
            room_type.enums,
            [
                "single_room",
                "shared_room",
                "bachelor_flat",
                "self_contained",
            ],
        )
        self.assertFalse(room_type.create_type)

    def test_status_uses_existing_postgresql_enum_and_dashboard_states(
        self,
    ) -> None:
        status = Listing.__table__.c.status.type

        self.assertIsInstance(status, ENUM)
        self.assertEqual(status.name, "listing_status_enum")
        self.assertEqual(
            status.enums,
            [
                "pending",
                "active",
                "taken",
                "expired",
                "removed",
                "draft",
                "closed",
            ],
        )
        self.assertFalse(status.create_type)


if __name__ == "__main__":
    unittest.main()
