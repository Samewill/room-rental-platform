from collections.abc import Sequence
import math

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

    def list_public_listings(
        self,
        *,
        center: tuple[float, float] | None = None,
        radius_km: int | None = None,
    ) -> list[PublicListingResponse]:
        if (center is None) != (radius_km is None):
            raise ValueError("A search center and radius must be provided together.")

        candidates = [
            listing
            for listing in self._repository.list_all()
            if self._is_published(listing)
        ]
        latest_decisions = self._repository.get_latest_moderation_decisions(
            [listing.listing_id for listing in candidates]
        )

        approved_listings = [
            listing
            for listing in candidates
            if latest_decisions.get(listing.listing_id) == self.APPROVED_DECISION
        ]
        if center is not None and radius_km is not None:
            return self._list_within_radius(
                approved_listings,
                center,
                radius_km,
            )

        return [self._to_public_response(listing) for listing in approved_listings]

    def _list_within_radius(
        self,
        listings: Sequence[Listing],
        center: tuple[float, float],
        radius_km: int,
    ) -> list[PublicListingResponse]:
        results: list[PublicListingResponse] = []
        for listing in listings:
            location = self._get_listing_coordinates(listing)
            if location is None or not self._is_location_within_radius(
                location,
                center,
                radius_km,
            ):
                continue
            results.append(
                self._to_public_response(listing, resolved_location=location),
            )
        return results

    def _get_listing_coordinates(
        self,
        listing: Listing,
    ) -> tuple[float, float] | None:
        if listing.latitude is not None and listing.longitude is not None:
            return listing.latitude, listing.longitude
        if listing.google_place_id:
            return self._google_places.get_location(listing.google_place_id)
        return None

    @staticmethod
    def _is_location_within_radius(
        location: tuple[float, float],
        center: tuple[float, float],
        radius_km: int,
    ) -> bool:
        latitude, longitude = location
        center_latitude, center_longitude = center
        latitude_difference = math.radians(latitude - center_latitude)
        longitude_difference = math.radians(longitude - center_longitude)
        haversine = (
            math.sin(latitude_difference / 2) ** 2
            + math.cos(math.radians(center_latitude))
            * math.cos(math.radians(latitude))
            * math.sin(longitude_difference / 2) ** 2
        )
        distance_km = 2 * 6371 * math.asin(math.sqrt(min(1.0, haversine)))
        return distance_km <= radius_km

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
    def _to_public_response(
        listing: Listing,
        *,
        resolved_location: tuple[float, float] | None = None,
    ) -> PublicListingResponse:
        response = PublicListingResponse.model_validate(listing)
        if resolved_location is not None:
            latitude, longitude = resolved_location
            return response.model_copy(
                update={
                    "has_map_location": True,
                    "approximate_latitude": round(latitude, 2),
                    "approximate_longitude": round(longitude, 2),
                },
            )
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
