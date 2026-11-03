"""Create web conversations and messages."""

from alembic import op
import sqlalchemy as sa


revision = "20261102_10"
down_revision = "20261102_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("contact_request_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contact_request_id"],
            ["contact_requests.request_id"],
            name="conversations_contact_request_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            name="conversations_pkey",
        ),
        sa.UniqueConstraint(
            "contact_request_id",
            name="conversations_contact_request_id_key",
        ),
    )
    op.create_table(
        "conversation_participants",
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="conversation_participants_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="conversation_participants_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            "user_id",
            name="conversation_participants_pkey",
        ),
    )
    op.create_index(
        "conversation_participants_user_id_idx",
        "conversation_participants",
        ["user_id"],
    )
    op.create_table(
        "messages",
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=8),
            server_default="sent",
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "length(trim(content)) BETWEEN 1 AND 4000",
            name="messages_content_length_check",
        ),
        sa.CheckConstraint(
            "status IN ('sent', 'read')",
            name="messages_status_check",
        ),
        sa.CheckConstraint(
            "(status = 'sent' AND read_at IS NULL) OR "
            "(status = 'read' AND read_at IS NOT NULL)",
            name="messages_read_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="messages_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id", "sender_id"],
            [
                "conversation_participants.conversation_id",
                "conversation_participants.user_id",
            ],
            name="messages_sender_participant_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("message_id", name="messages_pkey"),
    )
    op.create_index(
        "messages_conversation_sent_at_idx",
        "messages",
        ["conversation_id", "sent_at", "message_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "messages_conversation_sent_at_idx",
        table_name="messages",
    )
    op.drop_table("messages")
    op.drop_index(
        "conversation_participants_user_id_idx",
        table_name="conversation_participants",
    )
    op.drop_table("conversation_participants")
    op.drop_table("conversations")
