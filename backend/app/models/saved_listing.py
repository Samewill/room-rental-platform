from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SavedListing(Base):
    __tablename__ = "saved_listings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "listing_id",
            name="saved_listings_tenant_listing_key",
        ),
        Index("ix_saved_listings_tenant_id", "tenant_id"),
    )

    saved_listing_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="saved_listings_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="saved_listings_listing_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class ListingAlertDelivery(Base):
    __tablename__ = "listing_alert_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="listing_alert_deliveries_status_check",
        ),
        UniqueConstraint(
            "tenant_id",
            "listing_id",
            name="listing_alert_deliveries_tenant_listing_key",
        ),
        Index("ix_listing_alert_deliveries_listing_id", "listing_id"),
    )

    delivery_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="listing_alert_deliveries_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="listing_alert_deliveries_listing_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
