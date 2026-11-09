from app.models.listing import Listing
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import (
    PublicListingResponse,
)
from app.schemas.location import PublicListingLocationResponse
from app.services.google_places import GooglePlaces


class ListingService:
    PUBLISHED_STATUS = "active"
    APPROVED_DECISION = "approved"

    def __init__(
        self,
        repository: ListingRepository,
        google_places: GooglePlaces | None = None,
    ) -> None:
        self._repository = repository
        self._google_places = google_places or GooglePlaces()

    def list_public_listings(self) -> list[PublicListingResponse]:
        candidates = [
            listing
            for listing in self._repository.list_all()
            if self._is_published(listing)
        ]
        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id for listing in candidates]
        )

        return [
            self._to_public_response(listing)
            for listing in candidates
            if latest_decisions.get(listing.listing_id) == self.APPROVED_DECISION
        ]

    def get_public_listing(
        self,
        listing_id: int,
    ) -> PublicListingResponse | None:
        listing = self._repository.get_by_id(listing_id)
        if listing is None or not self._is_published(listing):
            return None

        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id]
        )
        if latest_decisions.get(listing.listing_id) != self.APPROVED_DECISION:
            return None

        return self._to_public_response(listing)

    def get_public_listing_location(
        self,
        listing_id: int,
    ) -> PublicListingLocationResponse | None:
        listing = self._repository.get_by_id(listing_id)
        if listing is None or not self._is_published(listing):
            return None

        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id]
        )
        if latest_decisions.get(listing.listing_id) != self.APPROVED_DECISION:
            return None

        if listing.latitude is not None and listing.longitude is not None:
            latitude, longitude = listing.latitude, listing.longitude
        elif listing.google_place_id:
            latitude, longitude = self._google_places.get_location(
                listing.google_place_id,
            )
        else:
            return None

        return PublicListingLocationResponse(
            approximate_latitude=round(latitude, 2),
            approximate_longitude=round(longitude, 2),
        )

    @classmethod
    def _is_published(cls, listing: Listing) -> bool:
        return listing.status == cls.PUBLISHED_STATUS

    @staticmethod
    def _to_public_response(listing: Listing) -> PublicListingResponse:
        response = PublicListingResponse.model_validate(listing)
        if listing.latitude is None or listing.longitude is None:
            return response.model_copy(
                update={"has_map_location": bool(listing.google_place_id)},
            )

        return response.model_copy(
            update={
                "has_map_location": True,
                "approximate_latitude": round(listing.latitude, 2),
                "approximate_longitude": round(listing.longitude, 2),
            },
        )
