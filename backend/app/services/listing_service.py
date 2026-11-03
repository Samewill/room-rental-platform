from app.models.listing import Listing
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingResponse


class ListingService:
    PUBLISHED_STATUS = "active"
    APPROVED_DECISION = "approved"

    def __init__(self, repository: ListingRepository) -> None:
        self._repository = repository

    def list_public_listings(self) -> list[ListingResponse]:
        candidates = [
            listing
            for listing in self._repository.list_all()
            if self._is_published(listing)
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
    ) -> ListingResponse | None:
        listing = self._repository.get_by_id(listing_id)
        if listing is None or not self._is_published(listing):
            return None

        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id]
        )
        if latest_decisions.get(listing.listing_id) != self.APPROVED_DECISION:
            return None

        return ListingResponse.model_validate(listing)

    @classmethod
    def _is_published(cls, listing: Listing) -> bool:
        return listing.status == cls.PUBLISHED_STATUS
