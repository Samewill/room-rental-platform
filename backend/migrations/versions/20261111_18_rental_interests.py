"""Add future rental interest opportunities and registrations."""

from alembic import op
import sqlalchemy as sa


revision = "20261111_18"
down_revision = "20261111_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rental_interest_opportunities",
        sa.Column(
            "opportunity_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=8),
            server_default="open",
            nullable=False,
        ),
        sa.Column("available_from", sa.Date(), nullable=False),
        sa.Column("available_until", sa.Date(), nullable=True),
        sa.Column("available_units", sa.Integer(), nullable=True),
        sa.Column(
            "max_active_registrations",
            sa.Integer(),
            server_default="50",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed')",
            name="rental_interest_opportunities_status_check",
        ),
        sa.CheckConstraint(
            "available_until IS NULL OR available_until >= available_from",
            name="rental_interest_opportunities_date_range_check",
        ),
        sa.CheckConstraint(
            "available_units IS NULL OR available_units BETWEEN 1 AND 500",
            name="rental_interest_opportunities_available_units_check",
        ),
        sa.CheckConstraint(
            "max_active_registrations BETWEEN 1 AND 500",
            name="rental_interest_opportunities_registration_limit_check",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.listing_id"],
            name="rental_interest_opportunities_listing_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "opportunity_id",
            name="rental_interest_opportunities_pkey",
        ),
    )
    op.create_index(
        "rental_interest_opportunities_one_open_listing_idx",
        "rental_interest_opportunities",
        ["listing_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "rental_interest_opportunities_listing_status_idx",
        "rental_interest_opportunities",
        ["listing_id", "status"],
    )

    op.create_table(
        "rental_interests",
        sa.Column(
            "interest_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("expected_move_in_date", sa.Date(), nullable=False),
        sa.Column("expected_duration_months", sa.Integer(), nullable=False),
        sa.Column("monthly_budget", sa.Numeric(10, 2), nullable=False),
        sa.Column("preferred_room_type", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply', 'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interests_status_check",
        ),
        sa.CheckConstraint(
            "expected_duration_months BETWEEN 1 AND 60",
            name="rental_interests_duration_check",
        ),
        sa.CheckConstraint(
            "monthly_budget > 0",
            name="rental_interests_monthly_budget_check",
        ),
        sa.CheckConstraint(
            "expires_at > registered_at",
            name="rental_interests_expiry_check",
        ),
        sa.CheckConstraint(
            "preferred_room_type IS NULL OR preferred_room_type IN "
            "('single_room', 'shared_room', 'bachelor_flat', 'self_contained')",
            name="rental_interests_preferred_room_type_check",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["rental_interest_opportunities.opportunity_id"],
            name="rental_interests_opportunity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users.user_id"],
            name="rental_interests_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interest_id",
            name="rental_interests_pkey",
        ),
    )
    op.create_index(
        "rental_interests_active_tenant_opportunity_idx",
        "rental_interests",
        ["opportunity_id", "tenant_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply')",
        ),
        sqlite_where=sa.text(
            "status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply')",
        ),
    )
    op.create_index(
        "rental_interests_tenant_registered_idx",
        "rental_interests",
        ["tenant_id", "registered_at"],
    )
    op.create_index(
        "rental_interests_opportunity_status_registered_idx",
        "rental_interests",
        ["opportunity_id", "status", "registered_at", "interest_id"],
    )

    op.create_table(
        "rental_interest_amenities",
        sa.Column("interest_id", sa.BigInteger(), nullable=False),
        sa.Column("amenity_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["amenity_id"],
            ["amenities.amenity_id"],
            name="rental_interest_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interest_id"],
            ["rental_interests.interest_id"],
            name="rental_interest_amenities_interest_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interest_id",
            "amenity_id",
            name="rental_interest_amenities_pkey",
        ),
    )

    op.create_table(
        "rental_interest_status_history",
        sa.Column(
            "history_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("interest_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "to_status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply', 'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interest_status_history_to_status_check",
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('active', 'waitlisted', 'contacted', 'invited_to_apply', "
            "'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interest_status_history_from_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.user_id"],
            name="rental_interest_status_history_actor_user_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["interest_id"],
            ["rental_interests.interest_id"],
            name="rental_interest_status_history_interest_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "history_id",
            name="rental_interest_status_history_pkey",
        ),
    )
    op.create_index(
        "rental_interest_status_history_interest_changed_idx",
        "rental_interest_status_history",
        ["interest_id", "changed_at", "history_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "rental_interest_status_history_interest_changed_idx",
        table_name="rental_interest_status_history",
    )
    op.drop_table("rental_interest_status_history")
    op.drop_table("rental_interest_amenities")
    op.drop_index(
        "rental_interests_opportunity_status_registered_idx",
        table_name="rental_interests",
    )
    op.drop_index(
        "rental_interests_tenant_registered_idx",
        table_name="rental_interests",
    )
    op.drop_index(
        "rental_interests_active_tenant_opportunity_idx",
        table_name="rental_interests",
    )
    op.drop_table("rental_interests")
    op.drop_index(
        "rental_interest_opportunities_listing_status_idx",
        table_name="rental_interest_opportunities",
    )
    op.drop_index(
        "rental_interest_opportunities_one_open_listing_idx",
        table_name="rental_interest_opportunities",
    )
    op.drop_table("rental_interest_opportunities")
