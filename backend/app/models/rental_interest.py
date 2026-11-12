from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.amenity import Amenity
from app.models.listing import Listing
from app.models.user import User


rental_interest_amenities = Table(
    "rental_interest_amenities",
    Base.metadata,
    Column(
        "interest_id",
        BigInteger,
        ForeignKey(
            "rental_interests.interest_id",
            name="rental_interest_amenities_interest_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "amenity_id",
        BigInteger,
        ForeignKey(
            "amenities.amenity_id",
            name="rental_interest_amenities_amenity_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)


class RentalInterestOpportunity(Base):
    __tablename__ = "rental_interest_opportunities"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'closed')",
            name="rental_interest_opportunities_status_check",
        ),
        CheckConstraint(
            "available_until IS NULL OR available_until >= available_from",
            name="rental_interest_opportunities_date_range_check",
        ),
        CheckConstraint(
            "available_units IS NULL OR available_units BETWEEN 1 AND 500",
            name="rental_interest_opportunities_available_units_check",
        ),
        CheckConstraint(
            "max_active_registrations BETWEEN 1 AND 500",
            name="rental_interest_opportunities_registration_limit_check",
        ),
        CheckConstraint(
            "expected_rental_duration_months IS NULL OR "
            "expected_rental_duration_months BETWEEN 1 AND 60",
            name="rental_interest_opportunities_duration_check",
        ),
        Index(
            "rental_interest_opportunities_one_open_listing_idx",
            "listing_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        Index(
            "rental_interest_opportunities_listing_status_idx",
            "listing_id",
            "status",
        ),
    )

    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "listings.listing_id",
            name="rental_interest_opportunities_listing_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="open",
    )
    available_from: Mapped[date] = mapped_column(Date, nullable=False)
    available_until: Mapped[date | None] = mapped_column(Date)
    available_units: Mapped[int | None] = mapped_column(Integer)
    max_active_registrations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="50",
    )
    waitlist_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    expected_rental_duration_months: Mapped[int | None] = mapped_column(
        Integer,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    listing: Mapped[Listing] = relationship(lazy="joined")


class RentalInterest(Base):
    __tablename__ = "rental_interests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply', 'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interests_status_check",
        ),
        CheckConstraint(
            "expected_duration_months BETWEEN 1 AND 60",
            name="rental_interests_duration_check",
        ),
        CheckConstraint(
            "monthly_budget > 0",
            name="rental_interests_monthly_budget_check",
        ),
        CheckConstraint(
            "expires_at > registered_at",
            name="rental_interests_expiry_check",
        ),
        CheckConstraint(
            "preferred_room_type IS NULL OR preferred_room_type IN "
            "('single_room', 'shared_room', 'bachelor_flat', 'self_contained')",
            name="rental_interests_preferred_room_type_check",
        ),
        Index(
            "rental_interests_active_tenant_opportunity_idx",
            "opportunity_id",
            "tenant_id",
            unique=True,
            postgresql_where=text(
                "status IN ('active', 'waitlisted', 'contacted', "
                "'invited_to_apply')",
            ),
            sqlite_where=text(
                "status IN ('active', 'waitlisted', 'contacted', "
                "'invited_to_apply')",
            ),
        ),
        Index(
            "rental_interests_tenant_registered_idx",
            "tenant_id",
            "registered_at",
        ),
        Index(
            "rental_interests_opportunity_status_registered_idx",
            "opportunity_id",
            "status",
            "registered_at",
            "interest_id",
        ),
    )

    interest_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rental_interest_opportunities.opportunity_id",
            name="rental_interests_opportunity_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="rental_interests_tenant_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    expected_move_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_duration_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    monthly_budget: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    preferred_room_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    required_amenities: Mapped[list[Amenity]] = relationship(
        secondary=rental_interest_amenities,
        lazy="selectin",
        order_by="Amenity.name",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="active",
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    opportunity: Mapped[RentalInterestOpportunity] = relationship(
        lazy="joined",
    )
    tenant: Mapped[User] = relationship(lazy="joined")
    history: Mapped[list[RentalInterestStatusHistory]] = relationship(
        back_populates="interest",
        cascade="all, delete-orphan",
        order_by="(RentalInterestStatusHistory.changed_at, "
        "RentalInterestStatusHistory.history_id)",
        lazy="selectin",
    )


class RentalInterestStatusHistory(Base):
    __tablename__ = "rental_interest_status_history"
    __table_args__ = (
        CheckConstraint(
            "to_status IN ('active', 'waitlisted', 'contacted', "
            "'invited_to_apply', 'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interest_status_history_to_status_check",
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('active', 'waitlisted', 'contacted', 'invited_to_apply', "
            "'converted', 'withdrawn', 'expired', 'closed')",
            name="rental_interest_status_history_from_status_check",
        ),
        Index(
            "rental_interest_status_history_interest_changed_idx",
            "interest_id",
            "changed_at",
            "history_id",
        ),
    )

    history_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    interest_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rental_interests.interest_id",
            name="rental_interest_status_history_interest_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="rental_interest_status_history_actor_user_id_fkey",
            ondelete="SET NULL",
        ),
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    note: Mapped[str | None] = mapped_column(Text)

    interest: Mapped[RentalInterest] = relationship(back_populates="history")
