from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ListingModeration(Base):
    __tablename__ = "listing_moderation"

    moderation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("listings.listing_id", name="listing_moderation_listing_id_fkey"),
        nullable=False,
    )
    admin_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", name="listing_moderation_admin_id_fkey"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        ENUM(
            "approved",
            "rejected",
            "flagged",
            name="moderation_decision_enum",
            create_type=False,
        ),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
