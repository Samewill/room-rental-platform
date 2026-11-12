import runpy
import unittest
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text


class SavedListingsAlertsMigrationTests(unittest.TestCase):
    def test_upgrade_preserves_existing_searches_and_adds_feature_schema(
        self,
    ) -> None:
        engine = create_engine("sqlite:///:memory:")
        versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"
        migrations = [
            runpy.run_path(
                str(versions / "20261111_14_saved_listings_and_alerts.py"),
            ),
            runpy.run_path(
                str(versions / "20261111_15_whatsapp_messaging.py"),
            ),
            runpy.run_path(
                str(
                    versions
                    / "20261111_16_merge_saved_alerts_whatsapp.py",
                ),
            ),
            runpy.run_path(
                str(
                    versions
                    / "20261111_17_reconcile_legacy_ai_schema.py",
                ),
            ),
        ]

        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE users (user_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text("CREATE TABLE listings (listing_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text(
                    "CREATE TABLE saved_searches ("
                    "saved_search_id INTEGER PRIMARY KEY, "
                    "tenant_id INTEGER NOT NULL, "
                    "location VARCHAR(255), "
                    "room_type VARCHAR(32), "
                    "minimum_rent NUMERIC(10, 2), "
                    "maximum_rent NUMERIC(10, 2), "
                    "created_at DATETIME NOT NULL)",
                ),
            )
            connection.execute(
                text(
                    "CREATE TABLE conversations ("
                    "conversation_id INTEGER PRIMARY KEY, "
                    "contact_request_id INTEGER NOT NULL, "
                    "created_at DATETIME NOT NULL)",
                ),
            )
            connection.execute(
                text("CREATE TABLE messages (message_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text(
                    "INSERT INTO users (user_id) VALUES (1)",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO listings (listing_id) VALUES (25)",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO saved_searches ("
                    "saved_search_id, tenant_id, location, created_at"
                    ") VALUES (5, 1, 'Rosebank', CURRENT_TIMESTAMP)",
                ),
            )

            for migration in migrations:
                with Operations.context(MigrationContext.configure(connection)):
                    migration["upgrade"]()

            saved_search = connection.execute(
                text(
                    "SELECT location, alerts_enabled, alerts_opted_in_at "
                    "FROM saved_searches WHERE saved_search_id = 5",
                ),
            ).one()
            self.assertEqual(saved_search[0], "Rosebank")
            self.assertFalse(saved_search[1])
            self.assertIsNone(saved_search[2])

            inspector = inspect(connection)
            table_names = set(inspector.get_table_names())
            self.assertTrue(
                {
                    "saved_listings",
                    "listing_alert_deliveries",
                    "whatsapp_contacts",
                    "whatsapp_messages",
                    "assistant_conversations",
                    "assistant_messages",
                }.issubset(table_names),
            )
            self.assertIn(
                "conversations_whatsapp_route_code_idx",
                {
                    index["name"]
                    for index in inspector.get_indexes("conversations")
                },
            )

            connection.execute(
                text(
                    "INSERT INTO saved_listings ("
                    "saved_listing_id, tenant_id, listing_id"
                    ") VALUES (1, 1, 25)",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO listing_alert_deliveries ("
                    "delivery_id, tenant_id, listing_id, status"
                    ") VALUES (1, 1, 25, 'pending')",
                ),
            )
            self.assertEqual(
                connection.execute(
                    text("SELECT count(*) FROM saved_listings"),
                ).scalar_one(),
                1,
            )
            self.assertEqual(
                connection.execute(
                    text("SELECT count(*) FROM listing_alert_deliveries"),
                ).scalar_one(),
                1,
            )

        engine.dispose()

    def test_reconciliation_preserves_existing_assistant_data(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"
        ai_migration = runpy.run_path(
            str(versions / "20261105_11_create_ai_assistant.py"),
        )
        reconciliation = runpy.run_path(
            str(versions / "20261111_17_reconcile_legacy_ai_schema.py"),
        )

        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE users (user_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text("INSERT INTO users (user_id) VALUES (1)"),
            )
            with Operations.context(MigrationContext.configure(connection)):
                ai_migration["upgrade"]()
            connection.execute(
                text(
                    "INSERT INTO assistant_conversations ("
                    "conversation_id, owner_user_id, assistant_role, "
                    "workflow_state"
                    ") VALUES (1, 1, 'tenant', '{}')",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO assistant_messages ("
                    "message_id, conversation_id, sender_role, content"
                    ") VALUES (1, 1, 'user', 'Keep this conversation')",
                ),
            )
            with Operations.context(MigrationContext.configure(connection)):
                reconciliation["upgrade"]()

            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT content FROM assistant_messages "
                        "WHERE message_id = 1",
                    ),
                ).scalar_one(),
                "Keep this conversation",
            )

        engine.dispose()

    def test_partial_assistant_schema_fails_without_replacing_tables(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"
        reconciliation = runpy.run_path(
            str(versions / "20261111_17_reconcile_legacy_ai_schema.py"),
        )

        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE assistant_conversations ("
                    "conversation_id INTEGER PRIMARY KEY)",
                ),
            )
            with Operations.context(MigrationContext.configure(connection)):
                with self.assertRaises(RuntimeError):
                    reconciliation["upgrade"]()

            self.assertEqual(
                inspect(connection).get_table_names(),
                ["assistant_conversations"],
            )

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
