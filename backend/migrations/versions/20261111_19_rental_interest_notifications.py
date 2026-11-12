"""Add in-app and WhatsApp rental-interest notifications."""

from alembic import op
import sqlalchemy as sa


revision = "20261111_19"
down_revision = "20261111_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rental_interest_notifications",
        sa.Column(
            "notification_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("interest_id", sa.BigInteger(), nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "whatsapp_delivery_status",
            sa.String(length=12),
            server_default="skipped",
            nullable=False,
        ),
        sa.Column("whatsapp_started_at", sa.DateTime(), nullable=True),
        sa.Column(
            "provider_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('interest_registered', "
            "'interest_status_updated', 'interest_promoted', "
            "'interest_expired', 'opportunity_closed', "
            "'interest_withdrawn')",
            name="rental_interest_notifications_event_type_check",
        ),
        sa.CheckConstraint(
            "whatsapp_delivery_status IN ('pending', 'sending', 'sent', "
            "'failed', 'skipped')",
            name="rental_interest_notifications_whatsapp_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.user_id"],
            name="rental_interest_notifications_recipient_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interest_id"],
            ["rental_interests.interest_id"],
            name="rental_interest_notifications_interest_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="rental_interest_notifications_listing_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "notification_id",
            name="rental_interest_notifications_pkey",
        ),
        sa.UniqueConstraint(
            "recipient_user_id",
            "event_key",
            name="rental_interest_notifications_recipient_event_key",
        ),
    )
    op.create_index(
        "rental_interest_notifications_recipient_created_idx",
        "rental_interest_notifications",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "rental_interest_notifications_whatsapp_status_idx",
        "rental_interest_notifications",
        ["whatsapp_delivery_status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "rental_interest_notifications_whatsapp_status_idx",
        table_name="rental_interest_notifications",
    )
    op.drop_index(
        "rental_interest_notifications_recipient_created_idx",
        table_name="rental_interest_notifications",
    )
    op.drop_table("rental_interest_notifications")
