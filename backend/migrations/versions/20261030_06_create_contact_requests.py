"""Create tenant contact requests."""

from alembic import op
import sqlalchemy as sa


revision = "20261030_06"
down_revision = "20261030_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("contact_requests"):
        expected_columns = {
            "request_id",
            "listing_id",
            "tenant_id",
            "status",
            "requested_at",
        }
        actual_columns = {
            column["name"] for column in inspector.get_columns("contact_requests")
        }
        constraint_names = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("contact_requests")
        }
        foreign_key_names = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys("contact_requests")
        }
        primary_key_name = inspector.get_pk_constraint("contact_requests")["name"]
        if (
            not expected_columns.issubset(actual_columns)
            or "contact_requests_status_check" not in constraint_names
            or not {
                "contact_requests_listing_id_fkey",
                "contact_requests_tenant_id_fkey",
            }.issubset(foreign_key_names)
            or primary_key_name != "contact_requests_pkey"
        ):
            raise RuntimeError(
                "The existing contact_requests table does not match the "
                "expected Phase 6 schema.",
            )
        return

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
    pass
