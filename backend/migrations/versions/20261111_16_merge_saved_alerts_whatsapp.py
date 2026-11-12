"""Merge the saved-alert and WhatsApp migration branches."""

from typing import Sequence


revision = "20261111_16"
down_revision: Sequence[str] = ("20261111_14", "20261111_15")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
