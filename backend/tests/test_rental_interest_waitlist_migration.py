import runpy
import unittest
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


class RentalInterestWaitlistMigrationTests(unittest.TestCase):
    @staticmethod
    def load_migration() -> dict[str, object]:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "20261111_20_interest_waitlist_settings.py"
        )
        return runpy.run_path(str(migration_path))

    def test_existing_opportunities_get_safe_defaults_and_duration_check(
        self,
    ) -> None:
        engine = create_engine("sqlite:///:memory:")
        migration = self.load_migration()

        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE rental_interest_opportunities ("
                    "opportunity_id INTEGER PRIMARY KEY, "
                    "available_from DATE NOT NULL, "
                    "available_until DATE, "
                    "available_units INTEGER, "
                    "max_active_registrations INTEGER NOT NULL)",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO rental_interest_opportunities "
                    "(opportunity_id, available_from, "
                    "max_active_registrations) "
                    "VALUES (1, '2027-01-01', 5)",
                ),
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration["upgrade"]()

            inspector = inspect(connection)
            self.assertTrue(
                {
                    "waitlist_enabled",
                    "expected_rental_duration_months",
                }.issubset(
                    {
                        column["name"]
                        for column in inspector.get_columns(
                            "rental_interest_opportunities",
                        )
                    },
                ),
            )
            row = connection.execute(
                text(
                    "SELECT waitlist_enabled, "
                    "expected_rental_duration_months "
                    "FROM rental_interest_opportunities "
                    "WHERE opportunity_id = 1",
                ),
            ).one()
            self.assertFalse(row.waitlist_enabled)
            self.assertIsNone(row.expected_rental_duration_months)

            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO rental_interest_opportunities "
                        "(opportunity_id, available_from, "
                        "max_active_registrations, waitlist_enabled, "
                        "expected_rental_duration_months) "
                        "VALUES (2, '2027-01-01', 5, 0, 61)",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
