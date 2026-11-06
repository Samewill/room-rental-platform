"""Add secure WhatsApp contact mappings and message routing."""

from alembic import op
import sqlalchemy as sa


revision = "20261105_11"
down_revision = "20261102_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
