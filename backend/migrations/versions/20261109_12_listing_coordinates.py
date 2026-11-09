"""Add optional map coordinates to listings."""

from alembic import op
import sqlalchemy as sa


revision = "20261109_12"
down_revision = "20261105_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("latitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("longitude", sa.Float(), nullable=True),
    )
    op.create_check_constraint(
        "listings_coordinates_pair_check",
        "listings",
        "(latitude IS NULL AND longitude IS NULL) OR "
        "(latitude IS NOT NULL AND longitude IS NOT NULL)",
    )
    op.create_check_constraint(
        "listings_latitude_range_check",
        "listings",
        "latitude IS NULL OR latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        "listings_longitude_range_check",
        "listings",
        "longitude IS NULL OR longitude BETWEEN -180 AND 180",
    )


def downgrade() -> None:
    op.drop_constraint(
        "listings_longitude_range_check",
        "listings",
        type_="check",
    )
    op.drop_constraint(
        "listings_latitude_range_check",
        "listings",
        type_="check",
    )
    op.drop_constraint(
        "listings_coordinates_pair_check",
        "listings",
        type_="check",
    )
    op.drop_column("listings", "longitude")
    op.drop_column("listings", "latitude")
