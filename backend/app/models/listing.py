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
from sqlalchemy.orm import Mapped, mapped_column

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
    room_type: Mapped[str] = mapped_column(String(14), nullable=False)
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
    status: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
