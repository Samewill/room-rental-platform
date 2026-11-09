"""Store Google Place IDs without persisting Google coordinates."""

from alembic import op
import sqlalchemy as sa


revision = "20261110_13"
down_revision = "20261109_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("google_place_id", sa.String(length=512), nullable=True),
    )
    op.create_check_constraint(
        "listings_google_place_coordinates_check",
        "listings",
        "google_place_id IS NULL OR "
        "(latitude IS NULL AND longitude IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "listings_google_place_coordinates_check",
        "listings",
        type_="check",
    )
    op.drop_column("listings", "google_place_id")
