"""Create tenant saved searches."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261102_07"
down_revision = "20261030_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column(
            "saved_search_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "room_type",
            postgresql.ENUM(
                "single_room",
                "shared_room",
                "bachelor_flat",
                "self_contained",
                name="room_type_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("minimum_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column("maximum_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "minimum_rent IS NULL OR minimum_rent >= 0",
            name="saved_searches_minimum_rent_check",
        ),
        sa.CheckConstraint(
            "maximum_rent IS NULL OR maximum_rent >= 0",
            name="saved_searches_maximum_rent_check",
        ),
        sa.CheckConstraint(
            "minimum_rent IS NULL OR maximum_rent IS NULL "
            "OR minimum_rent <= maximum_rent",
            name="saved_searches_rent_range_check",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users.user_id"],
            name="saved_searches_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "saved_search_id",
            name="saved_searches_pkey",
        ),
    )
    op.create_index(
        "ix_saved_searches_tenant_id",
        "saved_searches",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_searches_tenant_id",
        table_name="saved_searches",
    )
    op.drop_table("saved_searches")
