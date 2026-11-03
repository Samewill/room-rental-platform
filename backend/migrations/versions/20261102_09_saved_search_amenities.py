"""Support amenities on listings and saved searches."""

from alembic import op
import sqlalchemy as sa


revision = "20261102_09"
down_revision = "20261102_08"
branch_labels = None
depends_on = None


AMENITY_NAMES = ("Wi-Fi", "Parking", "Furnished", "Laundry")


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO amenities (name)
            VALUES (:wifi), (:parking), (:furnished), (:laundry)
            ON CONFLICT (name) DO NOTHING
            """
        ).bindparams(
            wifi=AMENITY_NAMES[0],
            parking=AMENITY_NAMES[1],
            furnished=AMENITY_NAMES[2],
            laundry=AMENITY_NAMES[3],
        )
    )
    op.create_table(
        "saved_search_amenities",
        sa.Column("saved_search_id", sa.BigInteger(), nullable=False),
        sa.Column("amenity_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["saved_search_id"],
            ["saved_searches.saved_search_id"],
            name="saved_search_amenities_saved_search_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["amenity_id"],
            ["amenities.amenity_id"],
            name="saved_search_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "saved_search_id",
            "amenity_id",
            name="saved_search_amenities_pkey",
        ),
    )


def downgrade() -> None:
    op.drop_table("saved_search_amenities")
