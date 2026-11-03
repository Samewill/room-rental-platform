from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="reviews_rating_check",
        ),
        UniqueConstraint(
            "contact_request_id",
            name="reviews_contact_request_id_key",
        ),
    )

    review_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    contact_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "contact_requests.request_id",
            name="reviews_contact_request_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
