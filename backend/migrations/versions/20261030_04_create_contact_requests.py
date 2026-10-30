"""Create tenant contact requests."""

from alembic import op
import sqlalchemy as sa


revision = "20261030_04"
down_revision = "20261029_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_requests",
        sa.Column(
            "request_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="contact_requests_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="contact_requests_listing_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users.user_id"],
            name="contact_requests_tenant_id_fkey",
        ),
        sa.PrimaryKeyConstraint("request_id", name="contact_requests_pkey"),
    )


def downgrade() -> None:
    op.drop_table("contact_requests")
