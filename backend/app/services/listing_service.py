from datetime import date

from app.models.listing import Listing
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingResponse


class ListingService:
    PUBLISHED_STATUS = "active"
    APPROVED_DECISION = "approved"

    def __init__(self, repository: ListingRepository) -> None:
        self._repository = repository

    def list_public_listings(
        self,
        as_of: date | None = None,
    ) -> list[ListingResponse]:
        today = as_of or date.today()
        candidates = [
            listing
            for listing in self._repository.list_all()
            if self._is_published_and_available(listing, today)
        ]
        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id for listing in candidates]
        )

        return [
            ListingResponse.model_validate(listing)
            for listing in candidates
            if latest_decisions.get(listing.listing_id) == self.APPROVED_DECISION
        ]

    def get_public_listing(
        self,
        listing_id: int,
        as_of: date | None = None,
    ) -> ListingResponse | None:
        today = as_of or date.today()
        listing = self._repository.get_by_id(listing_id)
        if listing is None or not self._is_published_and_available(listing, today):
            return None

        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id]
        )
        if latest_decisions.get(listing.listing_id) != self.APPROVED_DECISION:
            return None

        return ListingResponse.model_validate(listing)

    @classmethod
    def _is_published_and_available(cls, listing: Listing, today: date) -> bool:
        return (
            listing.status == cls.PUBLISHED_STATUS
            and listing.date_available <= today
        )
