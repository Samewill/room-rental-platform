from sqlalchemy import BigInteger, Column, ForeignKey, Identity, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


listing_amenities = Table(
    "listing_amenities",
    Base.metadata,
    Column(
        "listing_id",
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="listing_amenities_listing_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "amenity_id",
        BigInteger,
        ForeignKey(
            "amenities.amenity_id",
            name="listing_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)


class Amenity(Base):
    __tablename__ = "amenities"

    amenity_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    listings = relationship(
        "Listing",
        secondary=listing_amenities,
        back_populates="amenities",
    )
