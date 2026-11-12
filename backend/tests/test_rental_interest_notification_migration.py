import runpy
import unittest
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


class RentalInterestNotificationMigrationTests(unittest.TestCase):
    @staticmethod
    def load_migration() -> dict[str, object]:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "20261111_19_rental_interest_notifications.py"
        )
        return runpy.run_path(str(migration_path))

    def test_migration_adds_deduplicated_notification_outbox(self) -> None:
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
                    "CREATE TABLE rental_interests "
                    "(interest_id INTEGER PRIMARY KEY)",
                ),
            )
            connection.execute(text("INSERT INTO users VALUES (1)"))
            connection.execute(text("INSERT INTO listings VALUES (10)"))
            connection.execute(text("INSERT INTO rental_interests VALUES (20)"))

            with Operations.context(MigrationContext.configure(connection)):
                migration["upgrade"]()

            inspector = inspect(connection)
            self.assertIn(
                "rental_interest_notifications",
                inspector.get_table_names(),
            )
            self.assertIn(
                "rental_interest_notifications_recipient_created_idx",
                {
                    index["name"]
                    for index in inspector.get_indexes(
                        "rental_interest_notifications",
                    )
                },
            )
            insert = text(
                "INSERT INTO rental_interest_notifications "
                "(notification_id, recipient_user_id, interest_id, listing_id, "
                "event_key, event_type, title, body, "
                "whatsapp_delivery_status) "
                "VALUES (:notification_id, 1, 20, 10, :event_key, "
                "'interest_registered', 'New interest', 'Review the room', "
                "'skipped')",
            )
            connection.execute(
                insert,
                {"notification_id": 1, "event_key": "interest-20-event-1"},
            )
            with self.assertRaises(IntegrityError):
                connection.execute(
                    insert,
                    {
                        "notification_id": 2,
                        "event_key": "interest-20-event-1",
                    },
                )
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO rental_interest_notifications "
                        "(notification_id, recipient_user_id, interest_id, "
                        "listing_id, event_key, event_type, title, body, "
                        "whatsapp_delivery_status) "
                        "VALUES (3, 1, 20, 10, 'invalid-event', "
                        "'unknown', 'Invalid', 'Invalid', 'skipped')",
                    ),
                )

            with Operations.context(MigrationContext.configure(connection)):
                migration["downgrade"]()
            self.assertNotIn(
                "rental_interest_notifications",
                inspect(connection).get_table_names(),
            )

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
