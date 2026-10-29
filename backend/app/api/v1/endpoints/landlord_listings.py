import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.landlord_listing import (
    ListingCreateRequest,
    ListingUpdateRequest,
)
from app.schemas.listing import ListingResponse
from app.services.landlord_listing_service import (
    LandlordListingService,
    ListingAreaNotFoundError,
    ListingNotFoundError,
    ListingStateError,
)
from app.services.photo_storage import (
    PhotoStorageConfigurationError,
    PhotoStorageError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["landlord listings"])
landlord_dependency = require_role("landlord")
MAX_PHOTO_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_landlord_listing_service(
    db: Session = Depends(get_db),
) -> LandlordListingService:
    return LandlordListingService(db)


@router.get(
    "/users/me/listings",
    response_model=list[ListingResponse],
)
def list_my_listings(
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> list[ListingResponse]:
    try:
        return service.list_for_landlord(current_landlord.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve landlord listings")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing data is temporarily unavailable.",
        ) from exc


@router.post(
    "/listings",
    response_model=ListingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    changes: ListingCreateRequest,
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> ListingResponse:
    try:
        return service.create_listing(current_landlord.user_id, changes)
    except ListingAreaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Area does not exist.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to create listing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing could not be created right now.",
        ) from exc


@router.patch(
    "/listings/{listing_id}",
    response_model=ListingResponse,
)
def update_listing(
    changes: ListingUpdateRequest,
    listing_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> ListingResponse:
    try:
        return service.update_listing(
            current_landlord.user_id,
            listing_id,
            changes,
        )
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found.",
        ) from exc
    except ListingAreaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Area does not exist.",
        ) from exc
    except ListingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to update listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing could not be updated right now.",
        ) from exc


@router.post(
    "/listings/{listing_id}/submit",
    response_model=ListingResponse,
)
def submit_listing(
    listing_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> ListingResponse:
    try:
        return service.submit_listing(current_landlord.user_id, listing_id)
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found.",
        ) from exc
    except ListingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to submit listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing could not be submitted right now.",
        ) from exc


@router.post(
    "/listings/{listing_id}/withdraw",
    response_model=ListingResponse,
)
def withdraw_listing(
    listing_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> ListingResponse:
    try:
        return service.withdraw_listing(current_landlord.user_id, listing_id)
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to withdraw listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Listing could not be withdrawn right now.",
        ) from exc


@router.post(
    "/listings/{listing_id}/photos",
    response_model=ListingResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_listing_photo(
    listing_id: Annotated[int, Path(gt=0)],
    photo: Annotated[UploadFile, File()],
    current_landlord: User = Depends(landlord_dependency),
    service: LandlordListingService = Depends(get_landlord_listing_service),
) -> ListingResponse:
    if photo.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    image_size = len(photo.file.read(MAX_PHOTO_UPLOAD_BYTES + 1))
    if image_size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded image is empty.",
        )
    if image_size > MAX_PHOTO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The image must be 10 MB or smaller.",
        )
    photo.file.seek(0)

    try:
        return service.upload_photo(
            current_landlord.user_id,
            listing_id,
            photo.file,
        )
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found.",
        ) from exc
    except ListingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PhotoStorageConfigurationError as exc:
        logger.error("Cloudinary photo storage is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo uploads are not configured.",
        ) from exc
    except PhotoStorageError as exc:
        logger.exception("Cloudinary photo upload failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo upload is temporarily unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to save listing photo for listing %s", listing_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo upload is temporarily unavailable.",
        ) from exc
