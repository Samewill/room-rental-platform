from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.listing_moderation import ListingModeration
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingResponse


class ModerationListingNotFoundError(Exception):
    pass


class ModerationStateError(Exception):
    pass


class ModerationReasonRequiredError(Exception):
    pass


class ListingModerationService:
    APPROVED_DECISION = "approved"
    PENDING_STATUS = "pending"
    ACTIVE_STATUS = "active"
    DRAFT_STATUS = "draft"
    REMOVED_STATUS = "removed"
    REJECTED_DECISION = "rejected"
    FLAGGED_DECISION = "flagged"

    def __init__(self, db: Session) -> None:
        self._db = db
        self._listings = ListingRepository(db)

    def list_pending_listings(self) -> list[ListingResponse]:
        return [
            ListingResponse.model_validate(listing)
            for listing in self._listings.list_pending_listings()
        ]

    def list_published_listings(
        self,
        as_of: date | None = None,
    ) -> list[ListingResponse]:
        today = as_of or date.today()
        candidates = [
            listing
            for listing in self._listings.list_active_listings()
            if listing.date_available <= today
        ]
        latest_decisions = self._listings.get_latest_moderation_decisions(
            [listing.listing_id for listing in candidates]
        )
        return [
            ListingResponse.model_validate(listing)
            for listing in candidates
            if latest_decisions.get(listing.listing_id) == self.APPROVED_DECISION
        ]

    def get_moderation_history(
        self,
        listing_id: int,
    ) -> list[ListingModeration]:
        self._get_listing(listing_id)
        return self._listings.list_moderation_history(listing_id)

    def approve_listing(
        self,
        listing_id: int,
        admin_id: int,
        reason: str | None = None,
    ) -> ListingResponse:
        listing = self._get_listing(listing_id)
        self._require_status(listing, self.PENDING_STATUS)
        self._record_decision(
            listing,
            admin_id,
            self.APPROVED_DECISION,
            self._optional_reason(reason),
            self.ACTIVE_STATUS,
        )
        return ListingResponse.model_validate(listing)

    def reject_listing(
        self,
        listing_id: int,
        admin_id: int,
        reason: str,
    ) -> ListingResponse:
        listing = self._get_listing(listing_id)
        self._require_status(listing, self.PENDING_STATUS)
        self._record_decision(
            listing,
            admin_id,
            self.REJECTED_DECISION,
            self._required_reason(reason),
            self.DRAFT_STATUS,
        )
        return ListingResponse.model_validate(listing)

    def hide_listing(
        self,
        listing_id: int,
        admin_id: int,
        reason: str,
    ) -> ListingResponse:
        listing = self._get_listing(listing_id)
        self._require_status(listing, self.ACTIVE_STATUS)
        self._record_decision(
            listing,
            admin_id,
            self.FLAGGED_DECISION,
            self._required_reason(reason),
            self.REMOVED_STATUS,
        )
        return ListingResponse.model_validate(listing)

    def _get_listing(self, listing_id: int) -> Listing:
        listing = self._listings.get_by_id(listing_id)
        if listing is None:
            raise ModerationListingNotFoundError("Listing does not exist.")
        return listing

    @staticmethod
    def _require_status(listing: Listing, expected_status: str) -> None:
        if listing.status != expected_status:
            raise ModerationStateError(
                f"Only {expected_status} listings can be moderated this way.",
            )

    def _record_decision(
        self,
        listing: Listing,
        admin_id: int,
        decision: str,
        reason: str | None,
        new_status: str,
    ) -> None:
        try:
            self._listings.add_moderation_decision(
                listing.listing_id,
                admin_id,
                decision,
                reason,
            )
            listing.status = new_status
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    @staticmethod
    def _optional_reason(reason: str | None) -> str | None:
        if reason is None:
            return None
        normalized_reason = reason.strip()
        return normalized_reason or None

    @staticmethod
    def _required_reason(reason: str) -> str:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ModerationReasonRequiredError(
                "A reason is required for this moderation decision.",
            )
        return normalized_reason
