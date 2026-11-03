"""Align listing tables with the Phase 3 roadmap."""

from alembic import op
import sqlalchemy as sa


revision = "20261027_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("listing", "listings")
    op.rename_table("listing_photo", "listing_photos")

    op.create_table(
        "areas",
        sa.Column("area_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("area_id", name="areas_pkey"),
        sa.UniqueConstraint("name", name="areas_name_key"),
    )

    op.create_table(
        "amenities",
        sa.Column(
            "amenity_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("amenity_id", name="amenities_pkey"),
        sa.UniqueConstraint("name", name="amenities_name_key"),
    )

    op.add_column("listings", sa.Column("area_id", sa.BigInteger(), nullable=True))
    op.execute(
        sa.text(
            """
            INSERT INTO areas (name)
            SELECT DISTINCT btrim(suburb)
            FROM listings
            WHERE btrim(suburb) <> ''
            ON CONFLICT (name) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE listings
            SET area_id = areas.area_id
            FROM areas
            WHERE areas.name = btrim(listings.suburb)
            """
        )
    )

    connection = op.get_bind()
    unmapped_listings = connection.execute(
        sa.text("SELECT count(*) FROM listings WHERE area_id IS NULL")
    ).scalar_one()
    if unmapped_listings:
        raise RuntimeError(
            "Cannot migrate listings with blank or unmapped suburbs to areas."
        )

    op.alter_column("listings", "area_id", nullable=False)
    op.create_foreign_key(
        "listings_area_id_fkey",
        "listings",
        "areas",
        ["area_id"],
        ["area_id"],
    )
    op.drop_column("listings", "suburb")

    op.create_table(
        "listing_amenities",
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("amenity_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="listing_amenities_listing_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["amenity_id"],
            ["amenities.amenity_id"],
            name="listing_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "listing_id",
            "amenity_id",
            name="listing_amenities_pkey",
        ),
    )


def downgrade() -> None:
    op.drop_table("listing_amenities")
    op.add_column(
        "listings",
        sa.Column("suburb", sa.String(length=100), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE listings
            SET suburb = areas.name
            FROM areas
            WHERE areas.area_id = listings.area_id
            """
        )
    )
    op.alter_column("listings", "suburb", nullable=False)
    op.drop_column("listings", "area_id")
    op.drop_table("amenities")
    op.drop_table("areas")
    op.rename_table("listing_photos", "listing_photo")
    op.rename_table("listings", "listing")
