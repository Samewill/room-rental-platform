import runpy
import unittest
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


class WhatsAppMigrationTests(unittest.TestCase):
    @staticmethod
    def load_migration() -> dict[str, object]:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "20261111_15_whatsapp_messaging.py"
        )
        return runpy.run_path(str(migration_path))

    def test_migration_adds_routing_tables_and_unique_provider_ids(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        migration = self.load_migration()

        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE users (user_id INTEGER PRIMARY KEY)",
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
            with Operations.context(MigrationContext.configure(connection)):
                migration["upgrade"]()
                migration["upgrade"]()

            inspector = inspect(connection)
            self.assertIn("whatsapp_contacts", inspector.get_table_names())
            self.assertIn("whatsapp_messages", inspector.get_table_names())
            self.assertIn(
                "conversations_whatsapp_route_code_idx",
                {
                    index["name"]
                    for index in inspector.get_indexes("conversations")
                },
            )

            connection.execute(
                text(
                    "INSERT INTO whatsapp_messages ("
                    "whatsapp_message_id, provider_message_id, message_id, "
                    "conversation_id, sender_user_id, recipient_user_id, "
                    "direction, delivery_status"
                    ") VALUES (1, 'wamid.inbound', 1, 1, 1, 2, "
                    "'inbound', 'received')",
                ),
            )
            connection.execute(
                text(
                    "INSERT INTO whatsapp_messages ("
                    "whatsapp_message_id, provider_message_id, message_id, "
                    "conversation_id, sender_user_id, recipient_user_id, "
                    "direction, delivery_status"
                    ") VALUES (2, 'wamid.outbound', 1, 1, 1, 2, "
                    "'outbound', 'sent')",
                ),
            )
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO whatsapp_messages ("
                        "whatsapp_message_id, provider_message_id, message_id, "
                        "conversation_id, sender_user_id, recipient_user_id, "
                        "direction, delivery_status"
                        ") VALUES (3, 'wamid.inbound', 2, 1, 1, 2, "
                        "'inbound', 'received')",
                    ),
                )

            with Operations.context(MigrationContext.configure(connection)):
                migration["downgrade"]()
            inspector = inspect(connection)
            self.assertNotIn("whatsapp_contacts", inspector.get_table_names())
            self.assertNotIn("whatsapp_messages", inspector.get_table_names())
            self.assertNotIn(
                "whatsapp_route_code",
                {
                    column["name"]
                    for column in inspector.get_columns("conversations")
                },
            )

        engine.dispose()

    def test_partial_legacy_schema_fails_without_adding_objects(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        migration = self.load_migration()

        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE conversations (conversation_id INTEGER)"),
            )
            connection.execute(
                text("CREATE TABLE users (user_id INTEGER PRIMARY KEY)"),
            )
            connection.execute(
                text(
                    "CREATE TABLE messages (message_id INTEGER PRIMARY KEY)",
                ),
            )
            connection.execute(
                text("CREATE TABLE whatsapp_contacts (user_id INTEGER PRIMARY KEY)"),
            )

            with Operations.context(MigrationContext.configure(connection)):
                with self.assertRaises(RuntimeError):
                    migration["upgrade"]()

            self.assertNotIn(
                "whatsapp_messages",
                inspect(connection).get_table_names(),
            )
            self.assertNotIn(
                "whatsapp_route_code",
                {
                    column["name"]
                    for column in inspect(connection).get_columns(
                        "conversations",
                    )
                },
            )

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
