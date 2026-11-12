"""Add secure WhatsApp contact mappings and message routing."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261111_15"
down_revision = "20261102_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    whatsapp_tables = {"whatsapp_contacts", "whatsapp_messages"}
    route_code_exists = "whatsapp_route_code" in {
        column["name"]
        for column in inspector.get_columns("conversations")
    }

    if whatsapp_tables.issubset(tables) and route_code_exists:
        expected_columns = {
            "whatsapp_contacts": {
                "user_id",
                "encrypted_phone",
                "phone_lookup_hash",
                "verification_code_hash",
                "verification_expires_at",
                "verification_attempts",
                "verification_sent_at",
                "verified_at",
                "opted_in_at",
                "opted_out_at",
                "last_inbound_at",
                "created_at",
            },
            "whatsapp_messages": {
                "whatsapp_message_id",
                "provider_message_id",
                "message_id",
                "conversation_id",
                "sender_user_id",
                "recipient_user_id",
                "direction",
                "delivery_status",
                "created_at",
                "delivered_at",
            },
        }
        for table_name, required_columns in expected_columns.items():
            actual_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }
            if not required_columns.issubset(actual_columns):
                raise RuntimeError(
                    f"Existing {table_name} schema is incomplete; "
                    "refusing to alter it automatically.",
                )

        required_indexes = {
            "conversations": {"conversations_whatsapp_route_code_idx"},
            "whatsapp_messages": {
                "whatsapp_messages_conversation_direction_idx",
            },
        }
        for table_name, expected_indexes in required_indexes.items():
            actual_indexes = {
                index["name"]
                for index in inspector.get_indexes(table_name)
            }
            if not expected_indexes.issubset(actual_indexes):
                raise RuntimeError(
                    f"Existing {table_name} indexes are incomplete; "
                    "refusing to alter them automatically.",
                )

        required_constraints = {
            "whatsapp_contacts": {
                "whatsapp_contacts_pkey",
                "whatsapp_contacts_user_id_fkey",
                "whatsapp_contacts_phone_lookup_hash_key",
                "whatsapp_contacts_verification_attempts_check",
            },
            "whatsapp_messages": {
                "whatsapp_messages_pkey",
                "whatsapp_messages_conversation_id_fkey",
                "whatsapp_messages_message_id_fkey",
                "whatsapp_messages_sender_user_id_fkey",
                "whatsapp_messages_recipient_user_id_fkey",
                "whatsapp_messages_provider_message_id_key",
                "whatsapp_messages_direction_check",
                "whatsapp_messages_delivery_status_check",
            },
        }
        for table_name, expected_constraints in required_constraints.items():
            actual_constraints = {
                constraint["name"]
                for constraint in (
                    inspector.get_pk_constraint(table_name),
                    *inspector.get_foreign_keys(table_name),
                    *inspector.get_unique_constraints(table_name),
                    *inspector.get_check_constraints(table_name),
                )
                if constraint.get("name") is not None
            }
            if not expected_constraints.issubset(actual_constraints):
                raise RuntimeError(
                    f"Existing {table_name} constraints are incomplete; "
                    "refusing to alter them automatically.",
                )

        return

    if whatsapp_tables.intersection(tables) or route_code_exists:
        raise RuntimeError(
            "Existing WhatsApp schema is partial; refusing to create "
            "duplicate objects.",
        )

    op.add_column(
        "conversations",
        sa.Column("whatsapp_route_code", sa.String(length=12), nullable=True),
    )
    op.create_index(
        "conversations_whatsapp_route_code_idx",
        "conversations",
        ["whatsapp_route_code"],
        unique=True,
    )
    op.create_table(
        "whatsapp_contacts",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("encrypted_phone", sa.String(length=128), nullable=False),
        sa.Column("phone_lookup_hash", sa.String(length=64), nullable=False),
        sa.Column("verification_code_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "verification_expires_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "verification_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "verification_sent_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("opted_in_at", sa.DateTime(), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(), nullable=True),
        sa.Column("last_inbound_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verification_attempts BETWEEN 0 AND 5",
            name="whatsapp_contacts_verification_attempts_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="whatsapp_contacts_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            name="whatsapp_contacts_pkey",
        ),
        sa.UniqueConstraint(
            "phone_lookup_hash",
            name="whatsapp_contacts_phone_lookup_hash_key",
        ),
    )
    op.create_table(
        "whatsapp_messages",
        sa.Column(
            "whatsapp_message_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "provider_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_user_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("delivery_status", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="whatsapp_messages_direction_check",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('received', 'sent', 'failed')",
            name="whatsapp_messages_delivery_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="whatsapp_messages_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.message_id"],
            name="whatsapp_messages_message_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.user_id"],
            name="whatsapp_messages_recipient_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.user_id"],
            name="whatsapp_messages_sender_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "whatsapp_message_id",
            name="whatsapp_messages_pkey",
        ),
        sa.UniqueConstraint(
            "provider_message_id",
            name="whatsapp_messages_provider_message_id_key",
        ),
    )
    op.create_index(
        "whatsapp_messages_conversation_direction_idx",
        "whatsapp_messages",
        ["conversation_id", "direction"],
    )


def downgrade() -> None:
    op.drop_index(
        "whatsapp_messages_conversation_direction_idx",
        table_name="whatsapp_messages",
    )
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_contacts")
    op.drop_index(
        "conversations_whatsapp_route_code_idx",
        table_name="conversations",
    )
    op.drop_column("conversations", "whatsapp_route_code")
