"""Add waitlist controls and expected rental duration to opportunities."""

from alembic import op
import sqlalchemy as sa


revision = "20261111_20"
down_revision = "20261111_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rental_interest_opportunities") as batch_op:
        batch_op.add_column(
            sa.Column(
                "waitlist_enabled",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
        batch_op.add_column(
            sa.Column(
                "expected_rental_duration_months",
                sa.Integer(),
                nullable=True,
            ),
        )
        batch_op.create_check_constraint(
            "rental_interest_opportunities_duration_check",
            "expected_rental_duration_months IS NULL OR "
            "expected_rental_duration_months BETWEEN 1 AND 60",
        )


def downgrade() -> None:
    with op.batch_alter_table("rental_interest_opportunities") as batch_op:
        batch_op.drop_constraint(
            "rental_interest_opportunities_duration_check",
            type_="check",
        )
        batch_op.drop_column("expected_rental_duration_months")
        batch_op.drop_column("waitlist_enabled")
