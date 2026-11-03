"""Create reviews for approved contact requests."""

from alembic import op
import sqlalchemy as sa


revision = "20261102_08"
down_revision = "20261102_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column(
            "review_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("contact_request_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="reviews_rating_check",
        ),
        sa.ForeignKeyConstraint(
            ["contact_request_id"],
            ["contact_requests.request_id"],
            name="reviews_contact_request_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("review_id", name="reviews_pkey"),
        sa.UniqueConstraint(
            "contact_request_id",
            name="reviews_contact_request_id_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("reviews")
