from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.whatsapp_privacy import redact_phone_numbers
from app.models.amenity import Amenity
from app.models.listing import Listing
from app.models.rental_interest import RentalInterest, RentalInterestOpportunity
from app.models.rental_interest_notification import (
    RentalInterestNotification,
)
from app.models.whatsapp import WhatsAppContact
from app.repositories.amenity_repository import AmenityRepository
from app.repositories.listing_repository import ListingRepository
from app.repositories.rental_interest_repository import (
    ACTIVE_REGISTRATION_STATUSES,
    DUPLICATE_INTEREST_STATUSES,
    RentalInterestRepository,
)
from app.schemas.rental_interest import (
    InterestOpportunityRequest,
    InterestOpportunityResponse,
    InterestOpportunitySummary,
    RentalInterestCreateRequest,
    RentalInterestLandlordResponse,
    RentalInterestStatusHistoryResponse,
    RentalInterestTenantResponse,
)


class RentalInterestError(Exception):
    pass


class RentalInterestNotFoundError(RentalInterestError):
    pass


class RentalInterestForbiddenError(RentalInterestError):
    pass


class RentalInterestOpportunityUnavailableError(RentalInterestError):
    pass


class RentalInterestDuplicateError(RentalInterestError):
    pass


class RentalInterestStateError(RentalInterestError):
    pass


class RentalInterestCapacityError(RentalInterestError):
    pass


class RentalInterestCapacityFullError(RentalInterestCapacityError):
    pass


class RentalInterestWaitlistConsentRequiredError(RentalInterestCapacityError):
    pass


class RentalInterestAmenityError(RentalInterestError):
    pass


class RentalInterestRateLimitError(RentalInterestError):
    pass


class RentalInterestService:
    APPROVED_DECISION = "approved"
    OPEN_OPPORTUNITY_STATUS = "open"
    CLOSED_OPPORTUNITY_STATUS = "closed"
    ACTIVE_STATUS = "active"
    WAITLISTED_STATUS = "waitlisted"
    CONTACTED_STATUS = "contacted"
    INVITED_STATUS = "invited_to_apply"
    CONVERTED_STATUS = "converted"
    WITHDRAWN_STATUS = "withdrawn"
    EXPIRED_STATUS = "expired"
    CLOSED_STATUS = "closed"
    LANDLORD_TRANSITIONS = {
        ACTIVE_STATUS: {CONTACTED_STATUS, INVITED_STATUS},
        CONTACTED_STATUS: {INVITED_STATUS},
        INVITED_STATUS: {CONVERTED_STATUS},
    }

    def __init__(self, db: Session) -> None:
        self._db = db
        self._interests = RentalInterestRepository(db)
        self._listings = ListingRepository(db)
        self._amenities = AmenityRepository(db)
        settings = get_settings()
        self._expiry_days = settings.rental_interest_expiry_days
        self._max_submissions_per_day = (
            settings.rental_interest_max_submissions_per_day
        )

    def list_public_opportunities(self) -> list[InterestOpportunityResponse]:
        opportunities = self._interests.list_public_opportunities()
        latest_decisions = self._listings.get_latest_moderation_decisions(
            [opportunity.listing_id for opportunity in opportunities],
        )
        responses: list[InterestOpportunityResponse] = []
        seen_listing_ids: set[int] = set()
        for opportunity in opportunities:
            if opportunity.listing_id in seen_listing_ids:
                continue
            if not self._is_eligible_listing(
                opportunity.listing,
                latest_decisions.get(opportunity.listing_id),
            ):
                continue
            seen_listing_ids.add(opportunity.listing_id)
            responses.append(
                self._opportunity_response(opportunity, eligible=True),
            )
        return responses

    def list_for_landlord(
        self,
        landlord_id: int,
    ) -> list[InterestOpportunityResponse]:
        opportunities = self._interests.list_opportunities_for_landlord(
            landlord_id,
        )
        latest_decisions = self._listings.get_latest_moderation_decisions(
            [opportunity.listing_id for opportunity in opportunities],
        )
        return [
            self._opportunity_response(
                opportunity,
                eligible=self._is_eligible_listing(
                    opportunity.listing,
                    latest_decisions.get(opportunity.listing_id),
                ),
            )
            for opportunity in opportunities
        ]

    def save_opportunity(
        self,
        landlord_id: int,
        listing_id: int,
        changes: InterestOpportunityRequest,
    ) -> InterestOpportunityResponse:
        listing = self._listings.get_owned(listing_id, landlord_id)
        if listing is None:
            raise RentalInterestNotFoundError("Listing does not exist.")
        if not self._listing_is_eligible(listing):
            raise RentalInterestOpportunityUnavailableError(
                "Only active, approved listings can accept future interest.",
            )

        opportunity = self._interests.get_opportunity_for_listing(
            listing_id,
            for_update=True,
        )
        try:
            if opportunity is None:
                opportunity = RentalInterestOpportunity(
                    listing_id=listing_id,
                    status=self.OPEN_OPPORTUNITY_STATUS,
                    **changes.model_dump(),
                )
                self._interests.add_opportunity(opportunity)
            else:
                active_count = self._interests.count_registered(
                    opportunity.opportunity_id,
                )
                if changes.max_active_registrations < active_count:
                    raise RentalInterestCapacityError(
                        "The active registration limit cannot be lower than "
                        "the current active registration count.",
                    )
                existing_interests = self._interests.list_interests_for_landlord(
                    landlord_id,
                    opportunity_id=opportunity.opportunity_id,
                )
                if any(
                    interest.status in DUPLICATE_INTEREST_STATUSES
                    and (
                        interest.expected_move_in_date
                        < changes.available_from
                        or (
                            changes.available_until is not None
                            and interest.expected_move_in_date
                            > changes.available_until
                        )
                    )
                    for interest in existing_interests
                ):
                    raise RentalInterestCapacityError(
                        "Availability dates cannot exclude active or "
                        "waitlisted registrations. Close the opportunity "
                        "before changing its dates.",
                    )
                for field_name, value in changes.model_dump().items():
                    setattr(opportunity, field_name, value)
                opportunity.status = self.OPEN_OPPORTUNITY_STATUS
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._opportunity_response(opportunity, eligible=True)

    def close_opportunity(
        self,
        landlord_id: int,
        opportunity_id: int,
    ) -> InterestOpportunityResponse:
        opportunity = self._interests.get_opportunity(
            opportunity_id,
            for_update=True,
        )
        if opportunity is None:
            raise RentalInterestNotFoundError("Opportunity does not exist.")

        listing = self._listings.get_by_id(opportunity.listing_id)
        if listing is None:
            raise RentalInterestNotFoundError("Opportunity does not exist.")
        if listing.landlord_id != landlord_id:
            raise RentalInterestForbiddenError(
                "Only the listing's landlord can close this opportunity.",
            )

        try:
            self._close_opportunity(
                opportunity,
                actor_user_id=landlord_id,
                note="The landlord closed this opportunity.",
            )
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._opportunity_response(
            opportunity,
            eligible=self._listing_is_eligible(listing),
        )

    def create_interest(
        self,
        tenant_id: int,
        opportunity_id: int,
        changes: RentalInterestCreateRequest,
    ) -> RentalInterestTenantResponse:
        self._interests.lock_tenant(tenant_id)
        opportunity = self._interests.get_opportunity(
            opportunity_id,
            for_update=True,
        )
        if opportunity is None:
            raise RentalInterestOpportunityUnavailableError(
                "This opportunity is not accepting interest.",
            )
        listing = self._listings.get_by_id(opportunity.listing_id)
        if (
            opportunity.status != self.OPEN_OPPORTUNITY_STATUS
            or listing is None
            or not self._listing_is_eligible(listing)
        ):
            raise RentalInterestOpportunityUnavailableError(
                "This opportunity is not accepting interest.",
            )
        if listing.landlord_id == tenant_id:
            raise RentalInterestForbiddenError(
                "You cannot register interest in your own listing.",
            )
        if not self._move_in_is_available(
            changes.expected_move_in_date,
            opportunity,
        ):
            raise RentalInterestOpportunityUnavailableError(
                "The expected move-in date is outside this opportunity's "
                "availability window.",
            )
        if self._interests.get_duplicate(tenant_id, opportunity_id) is not None:
            raise RentalInterestDuplicateError(
                "You already have an active interest for this opportunity.",
            )

        now = self._now()
        if (
            self._interests.count_recent_submissions(
                tenant_id,
                now - timedelta(days=1),
            )
            >= self._max_submissions_per_day
        ):
            raise RentalInterestRateLimitError(
                "You have reached the daily interest registration limit.",
            )

        amenities = self._get_amenities(changes.required_amenities)
        active_count = self._interests.count_registered(opportunity_id)
        status_value = self.ACTIVE_STATUS
        if active_count >= opportunity.max_active_registrations:
            if not opportunity.waitlist_enabled:
                raise RentalInterestCapacityFullError(
                    "This opportunity is full and is not accepting "
                    "waitlist registrations.",
                )
            if not changes.join_waitlist:
                raise RentalInterestWaitlistConsentRequiredError(
                    "This opportunity is full. Explicit confirmation is "
                    "required to join its waiting list.",
                )
            status_value = self.WAITLISTED_STATUS
        interest = RentalInterest(
            opportunity_id=opportunity_id,
            tenant_id=tenant_id,
            expected_move_in_date=changes.expected_move_in_date,
            expected_duration_months=changes.expected_duration_months,
            monthly_budget=changes.monthly_budget,
            preferred_room_type=changes.preferred_room_type,
            required_amenities=amenities,
            status=status_value,
            registered_at=now,
            expires_at=now + timedelta(days=self._expiry_days),
            opportunity=opportunity,
        )
        try:
            self._interests.add_interest(interest)
            history = self._interests.add_history(
                interest,
                actor_user_id=tenant_id,
                from_status=None,
                to_status=status_value,
                note=(
                    "Waiting list: active registration limit reached."
                    if status_value == self.WAITLISTED_STATUS
                    else None
                ),
            )
            self._queue_notification(
                recipient_user_id=listing.landlord_id,
                interest=interest,
                history_id=history.history_id,
                event_type="interest_registered",
                title="New tenant interest",
                body=(
                    "A tenant registered interest in "
                    f"{listing.title}. Review the registration in your "
                    "landlord dashboard."
                ),
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if self._interests.get_duplicate(tenant_id, opportunity_id) is not None:
                raise RentalInterestDuplicateError(
                    "You already have an active interest for this opportunity.",
                ) from exc
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._tenant_response(interest)

    def list_for_tenant(
        self,
        tenant_id: int,
    ) -> list[RentalInterestTenantResponse]:
        return [
            self._tenant_response(interest)
            for interest in self._interests.list_for_tenant(tenant_id)
        ]

    def withdraw_interest(
        self,
        tenant_id: int,
        interest_id: int,
    ) -> RentalInterestTenantResponse:
        interest, opportunity = self._get_interest_and_lock_opportunity(
            interest_id,
        )
        if interest.tenant_id != tenant_id:
            raise RentalInterestForbiddenError(
                "Only the registering tenant can withdraw this interest.",
            )
        if interest.status not in DUPLICATE_INTEREST_STATUSES:
            raise RentalInterestStateError(
                "Only an active or waitlisted interest can be withdrawn.",
            )

        try:
            released_capacity = interest.status in ACTIVE_REGISTRATION_STATUSES
            self._set_status(
                interest,
                self.WITHDRAWN_STATUS,
                actor_user_id=tenant_id,
                note="Withdrawn by tenant.",
            )
            if released_capacity:
                self._promote_waitlist(opportunity, interest.interest_id)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._tenant_response(interest)

    def renew_interest(
        self,
        tenant_id: int,
        interest_id: int,
        *,
        join_waitlist: bool = False,
    ) -> RentalInterestTenantResponse:
        self._interests.lock_tenant(tenant_id)
        interest, opportunity = self._get_interest_and_lock_opportunity(
            interest_id,
        )
        if interest.tenant_id != tenant_id:
            raise RentalInterestForbiddenError(
                "Only the registering tenant can renew this interest.",
            )
        if interest.status != self.EXPIRED_STATUS:
            raise RentalInterestStateError(
                "Only an expired interest can be renewed.",
            )
        listing = self._listings.get_by_id(opportunity.listing_id)
        if (
            opportunity.status != self.OPEN_OPPORTUNITY_STATUS
            or listing is None
            or not self._listing_is_eligible(listing)
            or not self._move_in_is_available(
                interest.expected_move_in_date,
                opportunity,
            )
        ):
            raise RentalInterestOpportunityUnavailableError(
                "This interest cannot be renewed because the opportunity "
                "is no longer available for the expected move-in date.",
            )

        now = self._now()
        if (
            self._interests.count_recent_submissions(
                tenant_id,
                now - timedelta(days=1),
            )
            >= self._max_submissions_per_day
        ):
            raise RentalInterestRateLimitError(
                "You have reached the daily interest registration limit.",
            )

        duplicate = self._interests.get_duplicate(
            tenant_id,
            opportunity.opportunity_id,
        )
        if duplicate is not None and duplicate.interest_id != interest.interest_id:
            raise RentalInterestDuplicateError(
                "You already have an active interest for this opportunity.",
            )

        try:
            active_count = self._interests.count_registered(
                opportunity.opportunity_id,
            )
            new_status = self.ACTIVE_STATUS
            if active_count >= opportunity.max_active_registrations:
                if not opportunity.waitlist_enabled:
                    raise RentalInterestCapacityFullError(
                        "This opportunity is full and is not accepting "
                        "waitlist registrations.",
                    )
                if not join_waitlist:
                    raise RentalInterestWaitlistConsentRequiredError(
                        "This opportunity is full. Explicit confirmation is "
                        "required to join its waiting list.",
                    )
                new_status = self.WAITLISTED_STATUS
            interest.registered_at = now
            interest.expires_at = now + timedelta(days=self._expiry_days)
            self._set_status(
                interest,
                new_status,
                actor_user_id=tenant_id,
                note="Renewed by tenant.",
            )
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._tenant_response(interest)

    def update_status(
        self,
        landlord_id: int,
        interest_id: int,
        new_status: str,
    ) -> RentalInterestLandlordResponse:
        initial = self._interests.get_interest(interest_id)
        if initial is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        opportunity = self._interests.get_opportunity(
            initial.opportunity_id,
            for_update=True,
        )
        if opportunity is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        interest = self._interests.get_interest(
            interest_id,
            for_update=True,
        )
        if interest is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        listing = self._listings.get_by_id(opportunity.listing_id)
        if listing is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        if listing.landlord_id != landlord_id:
            raise RentalInterestForbiddenError(
                "Only the listing's landlord can update this interest.",
            )
        if (
            opportunity.status != self.OPEN_OPPORTUNITY_STATUS
            or not self._listing_is_eligible(listing)
        ):
            raise RentalInterestOpportunityUnavailableError(
                "This opportunity is no longer accepting interest.",
            )

        allowed = self.LANDLORD_TRANSITIONS.get(interest.status, set())
        if new_status not in allowed:
            raise RentalInterestStateError(
                f"Cannot change interest from {interest.status} to "
                f"{new_status}.",
            )

        try:
            self._set_status(
                interest,
                new_status,
                actor_user_id=landlord_id,
            )
            if new_status == self.CONVERTED_STATUS:
                self._promote_waitlist(opportunity, interest.interest_id)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return self._landlord_response(interest)

    def list_for_landlord_interests(
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
    ) -> list[RentalInterestLandlordResponse]:
        interests = self._interests.list_interests_for_landlord(
            landlord_id,
            opportunity_id=opportunity_id,
            move_in_from=move_in_from,
            move_in_until=move_in_until,
            minimum_budget=minimum_budget,
            maximum_budget=maximum_budget,
            preferred_room_type=preferred_room_type,
            required_amenities=required_amenities,
        )
        interests.sort(key=self._priority_key)
        return [
            self._landlord_response(interest)
            for interest in interests
        ]

    def expire_due_interests(self, *, now: datetime | None = None) -> int:
        current_time = now or self._now()
        open_opportunities = self._interests.list_open_opportunities()
        latest_decisions = self._listings.get_latest_moderation_decisions(
            [opportunity.listing_id for opportunity in open_opportunities],
        )
        due_opportunity_ids = sorted(
            {
                opportunity_id
                for opportunity_id, _ in self._interests.list_due(current_time)
            },
        )
        expired_count = 0
        try:
            for candidate in open_opportunities:
                if self._is_eligible_listing(
                    candidate.listing,
                    latest_decisions.get(candidate.listing_id),
                ):
                    continue
                opportunity = self._interests.get_opportunity(
                    candidate.opportunity_id,
                    for_update=True,
                )
                if (
                    opportunity is not None
                    and opportunity.status == self.OPEN_OPPORTUNITY_STATUS
                ):
                    listing = self._listings.get_by_id(opportunity.listing_id)
                    if listing is not None:
                        self._close_opportunity(
                            opportunity,
                            actor_user_id=None,
                            note=(
                                "Listing is no longer active and approved."
                            ),
                            landlord_id=listing.landlord_id,
                        )

            for opportunity_id in due_opportunity_ids:
                opportunity = self._interests.get_opportunity(
                    opportunity_id,
                    for_update=True,
                )
                if opportunity is None:
                    continue
                due_interests = self._interests.list_due_for_update(
                    opportunity_id,
                    current_time,
                )
                freed_capacity = False
                for interest in due_interests:
                    freed_capacity = (
                        freed_capacity
                        or interest.status in ACTIVE_REGISTRATION_STATUSES
                    )
                    self._set_status(
                        interest,
                        self.EXPIRED_STATUS,
                        actor_user_id=None,
                        note="Registration period expired.",
                    )
                    expired_count += 1
                if freed_capacity and opportunity.status == self.OPEN_OPPORTUNITY_STATUS:
                    self._promote_waitlist(opportunity, None)

            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        return expired_count

    def _close_opportunity(
        self,
        opportunity: RentalInterestOpportunity,
        *,
        actor_user_id: int | None,
        note: str,
        landlord_id: int | None = None,
    ) -> None:
        opportunity.status = self.CLOSED_OPPORTUNITY_STATUS
        listing = self._listings.get_by_id(opportunity.listing_id)
        target_landlord_id = landlord_id
        if target_landlord_id is None and listing is not None:
            target_landlord_id = listing.landlord_id
        if target_landlord_id is None:
            return
        interests = self._interests.list_interests_for_landlord(
            target_landlord_id,
            opportunity_id=opportunity.opportunity_id,
        )
        for interest in interests:
            if interest.status in DUPLICATE_INTEREST_STATUSES:
                self._set_status(
                    interest,
                    self.CLOSED_STATUS,
                    actor_user_id=actor_user_id,
                    note=note,
                )

    def _promote_waitlist(
        self,
        opportunity: RentalInterestOpportunity,
        excluded_interest_id: int | None,
    ) -> None:
        while (
            opportunity.status == self.OPEN_OPPORTUNITY_STATUS
            and self._interests.count_registered(opportunity.opportunity_id)
            < opportunity.max_active_registrations
        ):
            waitlisted = [
                interest
                for interest in self._interests.list_waitlisted(
                    opportunity.opportunity_id,
                )
                if interest.interest_id != excluded_interest_id
                and interest.expires_at > self._now()
            ]
            if not waitlisted:
                return
            waitlisted.sort(key=self._priority_key)
            self._set_status(
                waitlisted[0],
                self.ACTIVE_STATUS,
                actor_user_id=None,
                note="Promoted from the waiting list.",
            )

    def _get_interest_and_lock_opportunity(
        self,
        interest_id: int,
    ) -> tuple[RentalInterest, RentalInterestOpportunity]:
        initial = self._interests.get_interest(interest_id)
        if initial is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        opportunity = self._interests.get_opportunity(
            initial.opportunity_id,
            for_update=True,
        )
        if opportunity is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        interest = self._interests.get_interest(
            interest_id,
            for_update=True,
        )
        if interest is None:
            raise RentalInterestNotFoundError("Interest does not exist.")
        return interest, opportunity

    def _set_status(
        self,
        interest: RentalInterest,
        new_status: str,
        *,
        actor_user_id: int | None,
        note: str | None = None,
    ) -> None:
        old_status = interest.status
        if old_status == new_status:
            return
        interest.status = new_status
        history = self._interests.add_history(
            interest,
            actor_user_id=actor_user_id,
            from_status=old_status,
            to_status=new_status,
            note=note,
        )
        listing = interest.opportunity.listing
        if actor_user_id == interest.tenant_id:
            if new_status == self.WITHDRAWN_STATUS:
                self._queue_notification(
                    recipient_user_id=listing.landlord_id,
                    interest=interest,
                    history_id=history.history_id,
                    event_type="interest_withdrawn",
                    title="A tenant withdrew interest",
                    body=(
                        "A tenant withdrew interest in "
                        f"{listing.title}. Review remaining registrations "
                        "in your landlord dashboard."
                    ),
                )
            elif new_status == self.ACTIVE_STATUS:
                self._queue_notification(
                    recipient_user_id=listing.landlord_id,
                    interest=interest,
                    history_id=history.history_id,
                    event_type="interest_registered",
                    title="A tenant renewed interest",
                    body=(
                        "A tenant renewed interest in "
                        f"{listing.title}. Review the registration in your "
                        "landlord dashboard."
                    ),
                )
            return

        notification_details = {
            self.ACTIVE_STATUS: (
                "interest_promoted",
                "You are off the waitlist",
                (
                    f"Your interest in {listing.title} moved into the active "
                    "queue. This is not a reservation."
                ),
            ),
            self.CONVERTED_STATUS: (
                "interest_status_updated",
                "Your rental interest was marked as converted",
                (
                    f"The landlord marked your interest in {listing.title} "
                    "as converted. This is not a reservation; confirm any "
                    "rental directly."
                ),
            ),
            self.EXPIRED_STATUS: (
                "interest_expired",
                "Your rental interest expired",
                (
                    f"Your interest in {listing.title} expired. You can "
                    "renew it from your tenant dashboard if the opportunity "
                    "is still open."
                ),
            ),
            self.CLOSED_STATUS: (
                "opportunity_closed",
                "Future availability closed",
                (
                    f"The future availability opportunity for {listing.title} "
                    "has closed."
                ),
            ),
        }.get(
            new_status,
            (
                "interest_status_updated",
                "Your rental interest was updated",
                (
                    f"The landlord updated your interest in {listing.title} "
                    f"to {new_status.replace('_', ' ')}."
                ),
            ),
        )
        event_type, title, body = notification_details
        self._queue_notification(
            recipient_user_id=interest.tenant_id,
            interest=interest,
            history_id=history.history_id,
            event_type=event_type,
            title=title,
            body=body,
        )

    def _queue_notification(
        self,
        *,
        recipient_user_id: int,
        interest: RentalInterest,
        history_id: int,
        event_type: str,
        title: str,
        body: str,
    ) -> None:
        contact = self._db.get(WhatsAppContact, recipient_user_id)
        whatsapp_delivery_status = (
            "pending" if self._whatsapp_is_enabled(contact) else "skipped"
        )
        self._db.add(
            RentalInterestNotification(
                recipient_user_id=recipient_user_id,
                interest_id=interest.interest_id,
                listing_id=interest.opportunity.listing_id,
                event_key=(
                    f"rental-interest:{interest.interest_id}:"
                    f"history:{history_id}"
                ),
                event_type=event_type,
                title=redact_phone_numbers(title),
                body=redact_phone_numbers(body),
                whatsapp_delivery_status=whatsapp_delivery_status,
            ),
        )

    @staticmethod
    def _whatsapp_is_enabled(contact: WhatsAppContact | None) -> bool:
        return (
            isinstance(contact, WhatsAppContact)
            and contact.verified_at is not None
            and contact.opted_in_at is not None
            and contact.opted_out_at is None
        )

    def _get_amenities(self, names: list[str]) -> list[Amenity]:
        amenities = self._amenities.get_by_names(names)
        if {amenity.name for amenity in amenities} != set(names):
            raise RentalInterestAmenityError(
                "One or more selected amenities are unavailable.",
            )
        return amenities

    def _listing_is_eligible(self, listing: Listing) -> bool:
        latest_decisions = self._listings.get_latest_moderation_decisions(
            [listing.listing_id],
        )
        return self._is_eligible_listing(
            listing,
            latest_decisions.get(listing.listing_id),
        )

    @classmethod
    def _is_eligible_listing(
        cls,
        listing: Listing,
        latest_decision: str | None,
    ) -> bool:
        return (
            listing.status == "active"
            and latest_decision == cls.APPROVED_DECISION
        )

    @staticmethod
    def _move_in_is_available(
        move_in_date: date,
        opportunity: RentalInterestOpportunity,
    ) -> bool:
        return (
            move_in_date >= opportunity.available_from
            and (
                opportunity.available_until is None
                or move_in_date <= opportunity.available_until
            )
        )

    @staticmethod
    def _opportunity_summary(
        opportunity: RentalInterestOpportunity,
    ) -> InterestOpportunitySummary:
        listing = opportunity.listing
        return InterestOpportunitySummary(
            opportunity_id=opportunity.opportunity_id,
            listing_id=listing.listing_id,
            listing_title=listing.title,
            address=listing.address,
            area_name=listing.area.name,
            room_type=listing.room_type,
            monthly_rent=listing.monthly_rent,
            amenities=listing.amenity_names,
            available_from=opportunity.available_from,
            available_until=opportunity.available_until,
            available_units=opportunity.available_units,
            expected_rental_duration_months=(
                opportunity.expected_rental_duration_months
            ),
        )

    def _opportunity_response(
        self,
        opportunity: RentalInterestOpportunity,
        *,
        eligible: bool,
    ) -> InterestOpportunityResponse:
        active_registration_count = self._interests.count_registered(
            opportunity.opportunity_id,
        )
        if (
            not eligible
            or opportunity.status != self.OPEN_OPPORTUNITY_STATUS
            or (
                opportunity.available_until is not None
                and opportunity.available_until < date.today()
            )
        ):
            availability_status = "closed"
        elif active_registration_count >= opportunity.max_active_registrations:
            availability_status = "full"
        else:
            availability_status = "open"
        return InterestOpportunityResponse(
            **self._opportunity_summary(opportunity).model_dump(),
            status=opportunity.status,
            availability_status=availability_status,
            max_active_registrations=opportunity.max_active_registrations,
            active_registration_count=active_registration_count,
            waitlist_count=self._interests.count_status(
                opportunity.opportunity_id,
                (self.WAITLISTED_STATUS,),
            ),
            waitlist_enabled=opportunity.waitlist_enabled,
        )

    def _tenant_response(
        self,
        interest: RentalInterest,
    ) -> RentalInterestTenantResponse:
        return RentalInterestTenantResponse(
            interest_id=interest.interest_id,
            opportunity=self._opportunity_summary(interest.opportunity),
            expected_move_in_date=interest.expected_move_in_date,
            expected_duration_months=interest.expected_duration_months,
            monthly_budget=interest.monthly_budget,
            preferred_room_type=interest.preferred_room_type,
            required_amenities=[
                amenity.name for amenity in interest.required_amenities
            ],
            status=interest.status,
            registered_at=interest.registered_at,
            expires_at=interest.expires_at,
            history=[
                RentalInterestStatusHistoryResponse(
                    from_status=record.from_status,
                    to_status=record.to_status,
                    changed_at=record.changed_at,
                    note=record.note,
                )
                for record in interest.history
            ],
        )

    def _landlord_response(
        self,
        interest: RentalInterest,
    ) -> RentalInterestLandlordResponse:
        tenant_response = self._tenant_response(interest)
        score, reasons = self._compatibility(interest)
        return RentalInterestLandlordResponse(
            **tenant_response.model_dump(),
            tenant_name=interest.tenant.full_name,
            compatibility_score=score,
            compatibility_reasons=reasons,
        )

    @staticmethod
    def _compatibility(
        interest: RentalInterest,
    ) -> tuple[int, list[str]]:
        listing = interest.opportunity.listing
        days_from_availability = abs(
            (
                interest.expected_move_in_date
                - interest.opportunity.available_from
            ).days,
        )
        score = 0
        reasons: list[str] = [
            f"Move-in date is {days_from_availability} days from availability.",
        ]
        if Decimal(interest.monthly_budget) >= Decimal(listing.monthly_rent):
            score += 1
            reasons.append("Monthly budget covers the listing rent.")
        else:
            reasons.append("Monthly budget is below the listing rent.")

        if interest.preferred_room_type is None:
            reasons.append("No preferred room type was specified.")
        elif interest.preferred_room_type == listing.room_type:
            score += 1
            reasons.append("Preferred room type matches.")
        else:
            reasons.append("Preferred room type does not match.")

        required_amenities = {
            amenity.name for amenity in interest.required_amenities
        }
        if required_amenities:
            if required_amenities.issubset(set(listing.amenity_names)):
                score += 1
                reasons.append("All requested amenities are available.")
            else:
                reasons.append(
                    "One or more requested amenities are unavailable.",
                )
        else:
            reasons.append("No required amenities were specified.")
        return score, reasons

    @classmethod
    def _priority_key(
        cls,
        interest: RentalInterest,
    ) -> tuple[int, int, int, datetime, int]:
        score, _ = cls._compatibility(interest)
        opportunity = interest.opportunity
        date_distance = abs(
            (interest.expected_move_in_date - opportunity.available_from).days,
        )
        status_order = {
            cls.ACTIVE_STATUS: 0,
            cls.WAITLISTED_STATUS: 1,
            cls.CONTACTED_STATUS: 2,
            cls.INVITED_STATUS: 3,
            cls.CONVERTED_STATUS: 4,
            cls.EXPIRED_STATUS: 5,
            cls.WITHDRAWN_STATUS: 6,
            cls.CLOSED_STATUS: 7,
        }
        return (
            status_order.get(interest.status, 8),
            -score,
            date_distance,
            interest.registered_at,
            interest.interest_id,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
