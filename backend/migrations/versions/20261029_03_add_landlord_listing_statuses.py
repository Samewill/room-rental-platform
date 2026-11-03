"""Add draft and closed listing statuses."""

from alembic import op


revision = "20261029_03"
down_revision = "20261027_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE listing_status_enum ADD VALUE IF NOT EXISTS 'draft'")
    op.execute("ALTER TYPE listing_status_enum ADD VALUE IF NOT EXISTS 'closed'")


def downgrade() -> None:
    # PostgreSQL enum labels are retained to avoid invalidating existing rows.
    pass
