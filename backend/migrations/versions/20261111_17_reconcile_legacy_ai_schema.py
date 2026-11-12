"""Reconcile schemas behind the legacy duplicate revision ID."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261111_17"
down_revision = "20261111_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    assistant_tables = {
        "assistant_conversations",
        "assistant_messages",
    }

    if assistant_tables.issubset(tables):
        expected_columns = {
            "assistant_conversations": {
                "conversation_id",
                "owner_user_id",
                "assistant_role",
                "workflow_state",
                "created_at",
                "updated_at",
            },
            "assistant_messages": {
                "message_id",
                "conversation_id",
                "sender_role",
                "content",
                "payload",
                "created_at",
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
            "assistant_conversations": {
                "assistant_conversations_owner_updated_idx",
            },
            "assistant_messages": {
                "assistant_messages_conversation_created_idx",
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
            "assistant_conversations": {
                "assistant_conversations_pkey",
                "assistant_conversations_owner_user_id_fkey",
                "assistant_conversations_role_check",
            },
            "assistant_messages": {
                "assistant_messages_pkey",
                "assistant_messages_conversation_id_fkey",
                "assistant_messages_sender_role_check",
                "assistant_messages_content_length_check",
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

    if assistant_tables.intersection(tables):
        raise RuntimeError(
            "Existing AI assistant schema is partial; refusing to create "
            "duplicate objects.",
        )

    op.create_table(
        "assistant_conversations",
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("assistant_role", sa.Text(), nullable=False),
        sa.Column("workflow_state", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "assistant_role IN ('tenant', 'landlord')",
            name="assistant_conversations_role_check",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.user_id"],
            name="assistant_conversations_owner_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            name="assistant_conversations_pkey",
        ),
    )
    op.create_index(
        "assistant_conversations_owner_updated_idx",
        "assistant_conversations",
        ["owner_user_id", "updated_at"],
    )
    op.create_table(
        "assistant_messages",
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sender_role IN ('user', 'assistant')",
            name="assistant_messages_sender_role_check",
        ),
        sa.CheckConstraint(
            "length(trim(content)) BETWEEN 1 AND 4000",
            name="assistant_messages_content_length_check",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.conversation_id"],
            name="assistant_messages_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            name="assistant_messages_pkey",
        ),
    )
    op.create_index(
        "assistant_messages_conversation_created_idx",
        "assistant_messages",
        ["conversation_id", "created_at", "message_id"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "This compatibility migration is intentionally irreversible; "
        "it must not remove preserved assistant data.",
    )
