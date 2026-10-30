from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Listing(Base):
    __tablename__ = "listings"

    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    landlord_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", name="listings_landlord_id_fkey"),
        nullable=False,
    )
    area_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("areas.area_id", name="listings_area_id_fkey"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    room_type: Mapped[str] = mapped_column(
        ENUM(
            "single_room",
            "shared_room",
            "bachelor_flat",
            "self_contained",
            name="room_type_enum",
            create_type=False,
        ),
        nullable=False,
    )
    monthly_rent: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    date_available: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending",
            "active",
            "taken",
            "expired",
            "removed",
            "draft",
            "closed",
            name="listing_status_enum",
            create_type=False,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    photos: Mapped[list[ListingPhoto]] = relationship(
        back_populates="listing",
        lazy="selectin",
        order_by="ListingPhoto.photo_id",
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    photo_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="listing_photo_listing_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    listing: Mapped[Listing] = relationship(back_populates="photos")
