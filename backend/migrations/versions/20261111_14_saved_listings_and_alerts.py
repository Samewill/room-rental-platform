"""Add saved listings and WhatsApp saved-search alerts."""

from alembic import op
import sqlalchemy as sa


revision = "20261111_14"
down_revision = "20261110_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saved_searches",
        sa.Column(
            "alerts_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "saved_searches",
        sa.Column("alerts_opted_in_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "saved_listings",
        sa.Column(
            "saved_listing_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="saved_listings_listing_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users.user_id"],
            name="saved_listings_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "saved_listing_id",
            name="saved_listings_pkey",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "listing_id",
            name="saved_listings_tenant_listing_key",
        ),
    )
    op.create_index(
        "ix_saved_listings_tenant_id",
        "saved_listings",
        ["tenant_id"],
    )
    op.create_table(
        "listing_alert_deliveries",
        sa.Column(
            "delivery_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
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
            "status IN ('pending', 'sent', 'failed')",
            name="listing_alert_deliveries_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="listing_alert_deliveries_listing_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users.user_id"],
            name="listing_alert_deliveries_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "delivery_id",
            name="listing_alert_deliveries_pkey",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "listing_id",
            name="listing_alert_deliveries_tenant_listing_key",
        ),
    )
    op.create_index(
        "ix_listing_alert_deliveries_listing_id",
        "listing_alert_deliveries",
        ["listing_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_listing_alert_deliveries_listing_id",
        table_name="listing_alert_deliveries",
    )
    op.drop_table("listing_alert_deliveries")
    op.drop_index("ix_saved_listings_tenant_id", table_name="saved_listings")
    op.drop_table("saved_listings")
    op.drop_column("saved_searches", "alerts_opted_in_at")
    op.drop_column("saved_searches", "alerts_enabled")
