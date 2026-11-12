from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Column,
    CheckConstraint,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.amenity import Amenity


saved_search_amenities = Table(
    "saved_search_amenities",
    Base.metadata,
    Column(
        "saved_search_id",
        BigInteger,
        ForeignKey(
            "saved_searches.saved_search_id",
            name="saved_search_amenities_saved_search_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "amenity_id",
        BigInteger,
        ForeignKey(
            "amenities.amenity_id",
            name="saved_search_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    __table_args__ = (
        CheckConstraint(
            "minimum_rent IS NULL OR minimum_rent >= 0",
            name="saved_searches_minimum_rent_check",
        ),
        CheckConstraint(
            "maximum_rent IS NULL OR maximum_rent >= 0",
            name="saved_searches_maximum_rent_check",
        ),
        CheckConstraint(
            "minimum_rent IS NULL OR maximum_rent IS NULL "
            "OR minimum_rent <= maximum_rent",
            name="saved_searches_rent_range_check",
        ),
        Index("ix_saved_searches_tenant_id", "tenant_id"),
    )

    saved_search_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="saved_searches_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(String(255))
    room_type: Mapped[str | None] = mapped_column(
        ENUM(
            "single_room",
            "shared_room",
            "bachelor_flat",
            "self_contained",
            name="room_type_enum",
            create_type=False,
        ),
    )
    minimum_rent: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    maximum_rent: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    amenities: Mapped[list[Amenity]] = relationship(
        secondary=saved_search_amenities,
        lazy="selectin",
        order_by="Amenity.name",
    )
    alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    alerts_opted_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    @property
    def amenity_names(self) -> list[str]:
        return [amenity.name for amenity in self.amenities]
