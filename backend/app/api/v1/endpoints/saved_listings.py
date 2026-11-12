import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.listing import PublicListingResponse
from app.schemas.saved_listing import SavedListingStatusResponse
from app.services.saved_listing_service import (
    SavedListingService,
    SavedListingUnavailableError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["saved listings"])
tenant_dependency = require_role("tenant")


def get_saved_listing_service(
    db: Session = Depends(get_db),
) -> SavedListingService:
    return SavedListingService(db)


@router.get(
    "/me/saved-listings",
    response_model=list[PublicListingResponse],
)
def list_saved_listings(
    current_tenant: User = Depends(tenant_dependency),
    service: SavedListingService = Depends(get_saved_listing_service),
) -> list[PublicListingResponse]:
    try:
        return service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve tenant saved listings")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved listings are temporarily unavailable.",
        ) from exc


@router.get(
    "/me/saved-listings/{listing_id}",
    response_model=SavedListingStatusResponse,
)
def get_saved_listing_status(
    listing_id: int = Path(gt=0),
    current_tenant: User = Depends(tenant_dependency),
    service: SavedListingService = Depends(get_saved_listing_service),
) -> SavedListingStatusResponse:
    try:
        saved = service.is_saved(current_tenant.user_id, listing_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve saved listing status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved listing status is temporarily unavailable.",
        ) from exc
    return SavedListingStatusResponse(listing_id=listing_id, saved=saved)


@router.put(
    "/me/saved-listings/{listing_id}",
    response_model=SavedListingStatusResponse,
)
def save_listing(
    listing_id: int = Path(gt=0),
    current_tenant: User = Depends(tenant_dependency),
    service: SavedListingService = Depends(get_saved_listing_service),
) -> SavedListingStatusResponse:
    try:
        service.save_for_tenant(current_tenant.user_id, listing_id)
    except SavedListingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to save listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing could not be saved right now.",
        ) from exc
    return SavedListingStatusResponse(listing_id=listing_id, saved=True)


@router.delete(
    "/me/saved-listings/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_saved_listing(
    listing_id: int = Path(gt=0),
    current_tenant: User = Depends(tenant_dependency),
    service: SavedListingService = Depends(get_saved_listing_service),
) -> None:
    try:
        service.remove_for_tenant(current_tenant.user_id, listing_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to remove saved listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved listing could not be removed right now.",
        ) from exc
