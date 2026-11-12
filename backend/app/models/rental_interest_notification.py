from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RentalInterestNotification(Base):
    __tablename__ = "rental_interest_notifications"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('interest_registered', 'interest_status_updated', "
            "'interest_promoted', 'interest_expired', 'opportunity_closed', "
            "'interest_withdrawn')",
            name="rental_interest_notifications_event_type_check",
        ),
        CheckConstraint(
            "whatsapp_delivery_status IN ('pending', 'sending', 'sent', "
            "'failed', 'skipped')",
            name="rental_interest_notifications_whatsapp_status_check",
        ),
        UniqueConstraint(
            "recipient_user_id",
            "event_key",
            name="rental_interest_notifications_recipient_event_key",
        ),
        Index(
            "rental_interest_notifications_recipient_created_idx",
            "recipient_user_id",
            "created_at",
        ),
        Index(
            "rental_interest_notifications_whatsapp_status_idx",
            "whatsapp_delivery_status",
            "created_at",
        ),
    )

    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    recipient_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="rental_interest_notifications_recipient_user_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    interest_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rental_interests.interest_id",
            name="rental_interest_notifications_interest_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="rental_interest_notifications_listing_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    whatsapp_delivery_status: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        server_default="skipped",
    )
    whatsapp_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
