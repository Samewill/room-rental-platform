"""Create persistent AI assistant conversations."""

from alembic import op
import sqlalchemy as sa


revision = "20261105_11"
down_revision = "20261102_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.drop_index(
        "assistant_messages_conversation_created_idx",
        table_name="assistant_messages",
    )
    op.drop_table("assistant_messages")
    op.drop_index(
        "assistant_conversations_owner_updated_idx",
        table_name="assistant_conversations",
    )
    op.drop_table("assistant_conversations")
