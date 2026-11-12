import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import PublicListingResponse
from app.schemas.location import PublicListingLocationResponse
from app.services.google_places import GooglePlacesError
from app.services.listing_service import ListingService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/listings", tags=["listings"])


def get_listing_service(db: Session = Depends(get_db)) -> ListingService:
    return ListingService(ListingRepository(db))


@router.get("", response_model=list[PublicListingResponse])
def list_public_listings(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: int | None = Query(default=None, ge=5, le=10),
    service: ListingService = Depends(get_listing_service),
) -> list[PublicListingResponse]:
    try:
        if latitude is None and longitude is None and radius_km is None:
            return service.list_public_listings()
        if latitude is None or longitude is None or radius_km is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Latitude, longitude, and radius_km must be provided together."
                ),
            )
        if radius_km not in {5, 10}:
            raise HTTPException(
                status_code=422,
                detail="radius_km must be 5 or 10.",
            )
        return service.list_public_listings(
            center=(latitude, longitude),
            radius_km=radius_km,
        )
    except GooglePlacesError as exc:
        logger.exception("Failed to resolve listings for radius search")
        raise HTTPException(
            status_code=503,
            detail="Map locations are temporarily unavailable for radius search.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve public listings")
        raise HTTPException(
            status_code=503,
            detail="Listing data is temporarily unavailable.",
        ) from exc


@router.get("/{listing_id}", response_model=PublicListingResponse)
def get_public_listing(
    listing_id: int = Path(gt=0),
    service: ListingService = Depends(get_listing_service),
) -> PublicListingResponse:
    try:
        listing = service.get_public_listing(listing_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve public listing %s", listing_id)
        raise HTTPException(
            status_code=503,
            detail="Listing data is temporarily unavailable.",
        ) from exc

    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")

    return listing


@router.get(
    "/{listing_id}/map-location",
    response_model=PublicListingLocationResponse,
)
def get_public_listing_map_location(
    response: Response,
    listing_id: int = Path(gt=0),
    service: ListingService = Depends(get_listing_service),
) -> PublicListingLocationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        location = service.get_public_listing_location(listing_id)
    except GooglePlacesError as exc:
        logger.exception("Failed to resolve public map location")
        raise HTTPException(
            status_code=503,
            detail="Map location is temporarily unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to retrieve map location for listing %s",
            listing_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Listing data is temporarily unavailable.",
        ) from exc

    if location is None:
        raise HTTPException(status_code=404, detail="Map location not found.")

    return location
