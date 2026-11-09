from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
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
from app.models.area import Area
from app.models.amenity import Amenity, listing_amenities


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="listings_coordinates_pair_check",
        ),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="listings_latitude_range_check",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="listings_longitude_range_check",
        ),
        CheckConstraint(
            "google_place_id IS NULL OR "
            "(latitude IS NULL AND longitude IS NULL)",
            name="listings_google_place_coordinates_check",
        ),
    )

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
    area: Mapped[Area] = relationship(lazy="joined")
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
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
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
    amenities: Mapped[list[Amenity]] = relationship(
        secondary=listing_amenities,
        back_populates="listings",
        lazy="selectin",
        order_by="Amenity.name",
    )

    @property
    def amenity_names(self) -> list[str]:
        return [amenity.name for amenity in self.amenities]


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
