import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingResponse
from app.services.listing_service import ListingService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/listings", tags=["listings"])


def get_listing_service(db: Session = Depends(get_db)) -> ListingService:
    return ListingService(ListingRepository(db))


@router.get("", response_model=list[ListingResponse])
def list_public_listings(
    service: ListingService = Depends(get_listing_service),
) -> list[ListingResponse]:
    try:
        return service.list_public_listings()
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve public listings")
        raise HTTPException(
            status_code=503,
            detail="Listing data is temporarily unavailable.",
        ) from exc


@router.get("/{listing_id}", response_model=ListingResponse)
def get_public_listing(
    listing_id: int = Path(gt=0),
    service: ListingService = Depends(get_listing_service),
) -> ListingResponse:
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
