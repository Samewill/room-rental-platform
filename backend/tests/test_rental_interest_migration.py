import runpy
import unittest
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


class RentalInterestMigrationTests(unittest.TestCase):
    @staticmethod
    def load_migration() -> dict[str, object]:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "20261111_18_rental_interests.py"
        )
        return runpy.run_path(str(migration_path))

    def test_migration_creates_constraints_and_status_history(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        migration = self.load_migration()

        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE users (user_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text("CREATE TABLE listings (listing_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text(
                    "CREATE TABLE amenities (amenity_id INTEGER PRIMARY KEY)",
                ),
            )
            connection.execute(text("INSERT INTO users VALUES (1), (2)"))
            connection.execute(text("INSERT INTO listings VALUES (10)"))
            connection.execute(text("INSERT INTO amenities VALUES (20)"))

            with Operations.context(MigrationContext.configure(connection)):
                migration["upgrade"]()

            inspector = inspect(connection)
            self.assertTrue(
                {
                    "rental_interest_opportunities",
                    "rental_interests",
                    "rental_interest_amenities",
                    "rental_interest_status_history",
                }.issubset(inspector.get_table_names()),
            )
            self.assertIn(
                "rental_interests_active_tenant_opportunity_idx",
                {
                    index["name"]
                    for index in inspector.get_indexes("rental_interests")
                },
            )

            connection.execute(
                text(
                    "INSERT INTO rental_interest_opportunities "
                    "(opportunity_id, listing_id, status, available_from) "
                    "VALUES (1, 10, 'open', '2027-01-01')",
                ),
            )
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO rental_interest_opportunities "
                        "(opportunity_id, listing_id, status, available_from) "
                        "VALUES (2, 10, 'open', '2027-02-01')",
                    ),
                )
            connection.execute(
                text(
                    "INSERT INTO rental_interest_opportunities "
                    "(opportunity_id, listing_id, status, available_from) "
                    "VALUES (2, 10, 'closed', '2027-02-01')",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO rental_interests "
                    "(interest_id, opportunity_id, tenant_id, "
                    "expected_move_in_date, expected_duration_months, "
                    "monthly_budget, status, expires_at) "
                    "VALUES (1, 1, 1, '2027-01-15', 12, 5000, "
                    "'active', '2027-04-01')",
                ),
            )
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO rental_interests "
                        "(interest_id, opportunity_id, tenant_id, "
                        "expected_move_in_date, expected_duration_months, "
                        "monthly_budget, status, expires_at) "
                        "VALUES (2, 1, 1, '2027-01-20', 12, 5000, "
                        "'waitlisted', '2027-04-01')",
                    ),
                )
            connection.execute(
                text(
                    "UPDATE rental_interests SET status = 'withdrawn' "
                    "WHERE interest_id = 1",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO rental_interests "
                    "(interest_id, opportunity_id, tenant_id, "
                    "expected_move_in_date, expected_duration_months, "
                    "monthly_budget, status, expires_at) "
                    "VALUES (3, 1, 1, '2027-01-20', 12, 5000, "
                    "'active', '2027-04-01')",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO rental_interest_status_history "
                    "(history_id, interest_id, actor_user_id, from_status, "
                    "to_status) VALUES (1, 3, 1, NULL, 'active')",
                ),
            )
            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT to_status FROM rental_interest_status_history "
                        "WHERE interest_id = 3",
                    ),
                ).scalar_one(),
                "active",
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration["downgrade"]()
            self.assertNotIn(
                "rental_interests",
                inspect(connection).get_table_names(),
            )

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
