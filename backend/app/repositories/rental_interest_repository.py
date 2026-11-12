from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, lazyload, selectinload

from app.models.amenity import Amenity
from app.models.listing import Listing
from app.models.rental_interest import (
    RentalInterest,
    RentalInterestOpportunity,
    RentalInterestStatusHistory,
)
from app.models.user import User


ACTIVE_REGISTRATION_STATUSES = (
    "active",
    "contacted",
    "invited_to_apply",
)
DUPLICATE_INTEREST_STATUSES = (
    "active",
    "waitlisted",
    "contacted",
    "invited_to_apply",
)


class RentalInterestRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def lock_tenant(self, tenant_id: int) -> None:
        self._db.execute(
            select(User.user_id)
            .where(User.user_id == tenant_id)
            .with_for_update(of=User),
        ).scalar_one()

    def count_recent_submissions(
        self,
        tenant_id: int,
        since: datetime,
    ) -> int:
        statement = select(func.count()).select_from(RentalInterest).where(
            RentalInterest.tenant_id == tenant_id,
            RentalInterest.registered_at >= since,
        )
        return int(self._db.scalar(statement) or 0)

    def get_opportunity(
        self,
        opportunity_id: int,
        *,
        for_update: bool = False,
    ) -> RentalInterestOpportunity | None:
        statement = (
            select(RentalInterestOpportunity)
            .options(lazyload(RentalInterestOpportunity.listing))
            .where(
                RentalInterestOpportunity.opportunity_id == opportunity_id,
            )
        )
        if for_update:
            statement = statement.with_for_update(
                of=RentalInterestOpportunity,
            )
        return self._db.scalar(statement)

    def get_opportunity_for_listing(
        self,
        listing_id: int,
        *,
        for_update: bool = False,
    ) -> RentalInterestOpportunity | None:
        statement = (
            select(RentalInterestOpportunity)
            .options(lazyload(RentalInterestOpportunity.listing))
            .where(RentalInterestOpportunity.listing_id == listing_id)
            .order_by(
                (RentalInterestOpportunity.status != "open").asc(),
                RentalInterestOpportunity.opportunity_id.desc(),
            )
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update(
                of=RentalInterestOpportunity,
            )
        return self._db.scalar(statement)

    def list_public_opportunities(self) -> list[RentalInterestOpportunity]:
        statement = (
            select(RentalInterestOpportunity)
            .options(
                joinedload(RentalInterestOpportunity.listing).selectinload(
                    Listing.amenities,
                ),
            )
            .order_by(
                RentalInterestOpportunity.listing_id,
                (RentalInterestOpportunity.status != "open").asc(),
                RentalInterestOpportunity.opportunity_id.desc(),
            )
        )
        return list(self._db.scalars(statement).unique().all())

    def list_open_opportunities(self) -> list[RentalInterestOpportunity]:
        statement = (
            select(RentalInterestOpportunity)
            .options(
                joinedload(RentalInterestOpportunity.listing).selectinload(
                    Listing.amenities,
                ),
            )
            .where(RentalInterestOpportunity.status == "open")
            .order_by(
                RentalInterestOpportunity.available_from,
                RentalInterestOpportunity.opportunity_id,
            )
        )
        return list(self._db.scalars(statement).unique().all())

    def list_opportunities_for_landlord(
        self,
        landlord_id: int,
    ) -> list[RentalInterestOpportunity]:
        statement = (
            select(RentalInterestOpportunity)
            .join(
                Listing,
                Listing.listing_id
                == RentalInterestOpportunity.listing_id,
            )
            .options(
                joinedload(RentalInterestOpportunity.listing).selectinload(
                    Listing.amenities,
                ),
            )
            .where(Listing.landlord_id == landlord_id)
            .order_by(
                Listing.listing_id,
                (RentalInterestOpportunity.status != "open").asc(),
                RentalInterestOpportunity.opportunity_id.desc(),
            )
        )
        return list(self._db.scalars(statement).unique().all())

    def add_opportunity(
        self,
        opportunity: RentalInterestOpportunity,
    ) -> RentalInterestOpportunity:
        self._db.add(opportunity)
        self._db.flush()
        return opportunity

    def get_interest(
        self,
        interest_id: int,
        *,
        for_update: bool = False,
    ) -> RentalInterest | None:
        statement = (
            select(RentalInterest)
            .options(lazyload(RentalInterest.opportunity))
            .where(RentalInterest.interest_id == interest_id)
        )
        if for_update:
            statement = statement.with_for_update(of=RentalInterest)
        return self._db.scalar(statement)

    def get_duplicate(
        self,
        tenant_id: int,
        opportunity_id: int,
    ) -> RentalInterest | None:
        statement = select(RentalInterest).where(
            RentalInterest.tenant_id == tenant_id,
            RentalInterest.opportunity_id == opportunity_id,
            RentalInterest.status.in_(DUPLICATE_INTEREST_STATUSES),
        )
        return self._db.scalar(statement)

    def count_status(
        self,
        opportunity_id: int,
        statuses: tuple[str, ...],
    ) -> int:
        statement = select(func.count()).select_from(RentalInterest).where(
            RentalInterest.opportunity_id == opportunity_id,
            RentalInterest.status.in_(statuses),
        )
        return int(self._db.scalar(statement) or 0)

    def count_registered(
        self,
        opportunity_id: int,
    ) -> int:
        return self.count_status(opportunity_id, ACTIVE_REGISTRATION_STATUSES)

    def list_waitlisted(
        self,
        opportunity_id: int,
    ) -> list[RentalInterest]:
        statement = (
            select(RentalInterest)
            .options(
                selectinload(RentalInterest.required_amenities),
                joinedload(RentalInterest.tenant),
            )
            .where(
                RentalInterest.opportunity_id == opportunity_id,
                RentalInterest.status == "waitlisted",
            )
            .order_by(
                RentalInterest.registered_at,
                RentalInterest.interest_id,
            )
        )
        return list(self._db.scalars(statement).unique().all())

    def list_for_tenant(self, tenant_id: int) -> list[RentalInterest]:
        statement = (
            select(RentalInterest)
            .options(
                joinedload(RentalInterest.opportunity).joinedload(
                    RentalInterestOpportunity.listing,
                ),
                selectinload(RentalInterest.required_amenities),
                selectinload(RentalInterest.history),
            )
            .where(RentalInterest.tenant_id == tenant_id)
            .order_by(
                RentalInterest.registered_at.desc(),
                RentalInterest.interest_id.desc(),
            )
        )
        return list(self._db.scalars(statement).unique().all())

    def list_interests_for_landlord(
        self,
        landlord_id: int,
        *,
        opportunity_id: int | None = None,
        move_in_from: date | None = None,
        move_in_until: date | None = None,
        minimum_budget: Decimal | None = None,
        maximum_budget: Decimal | None = None,
        preferred_room_type: str | None = None,
        required_amenities: list[str] | None = None,
    ) -> list[RentalInterest]:
        statement = (
            select(RentalInterest)
            .join(
                RentalInterestOpportunity,
                RentalInterestOpportunity.opportunity_id
                == RentalInterest.opportunity_id,
            )
            .join(
                Listing,
                Listing.listing_id
                == RentalInterestOpportunity.listing_id,
            )
            .options(
                joinedload(RentalInterest.opportunity).joinedload(
                    RentalInterestOpportunity.listing,
                ),
                joinedload(RentalInterest.tenant),
                selectinload(RentalInterest.required_amenities),
                selectinload(RentalInterest.history),
            )
            .where(Listing.landlord_id == landlord_id)
        )
        if opportunity_id is not None:
            statement = statement.where(
                RentalInterest.opportunity_id == opportunity_id,
            )
        if move_in_from is not None:
            statement = statement.where(
                RentalInterest.expected_move_in_date >= move_in_from,
            )
        if move_in_until is not None:
            statement = statement.where(
                RentalInterest.expected_move_in_date <= move_in_until,
            )
        if minimum_budget is not None:
            statement = statement.where(
                RentalInterest.monthly_budget >= minimum_budget,
            )
        if maximum_budget is not None:
            statement = statement.where(
                RentalInterest.monthly_budget <= maximum_budget,
            )
        if preferred_room_type is not None:
            statement = statement.where(
                RentalInterest.preferred_room_type == preferred_room_type,
            )
        for amenity_name in required_amenities or []:
            statement = statement.where(
                RentalInterest.required_amenities.any(
                    Amenity.name == amenity_name,
                ),
            )
        statement = statement.order_by(
            RentalInterest.registered_at,
            RentalInterest.interest_id,
        )
        return list(self._db.scalars(statement).unique().all())

    def list_due(self, now: datetime) -> list[tuple[int, int]]:
        statement = (
            select(
                RentalInterest.opportunity_id,
                RentalInterest.interest_id,
            )
            .where(
                RentalInterest.status.in_(DUPLICATE_INTEREST_STATUSES),
                RentalInterest.expires_at <= now,
            )
            .order_by(
                RentalInterest.opportunity_id,
                RentalInterest.interest_id,
            )
        )
        return [
            (row.opportunity_id, row.interest_id)
            for row in self._db.execute(statement)
        ]

    def list_due_for_update(
        self,
        opportunity_id: int,
        now: datetime,
    ) -> list[RentalInterest]:
        statement = (
            select(RentalInterest)
            .where(
                RentalInterest.opportunity_id == opportunity_id,
                RentalInterest.status.in_(DUPLICATE_INTEREST_STATUSES),
                RentalInterest.expires_at <= now,
            )
            .order_by(RentalInterest.interest_id)
            .with_for_update(of=RentalInterest)
        )
        return list(self._db.scalars(statement).all())

    def add_interest(self, interest: RentalInterest) -> RentalInterest:
        self._db.add(interest)
        self._db.flush()
        return interest

    def add_history(
        self,
        interest: RentalInterest,
        *,
        actor_user_id: int | None,
        from_status: str | None,
        to_status: str,
        note: str | None = None,
    ) -> RentalInterestStatusHistory:
        history = RentalInterestStatusHistory(
            interest=interest,
            actor_user_id=actor_user_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
        self._db.add(history)
        self._db.flush()
        return history
