import logging
from typing import Annotated, NoReturn

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import LandlordRoleGrantResponse
from app.schemas.listing import ListingResponse
from app.schemas.listing_moderation import (
    ListingModerationResponse,
    ModerationApprovalRequest,
    ModerationReasonRequest,
)
from app.services.listing_moderation_service import (
    ListingModerationService,
    ModerationListingNotFoundError,
    ModerationReasonRequiredError,
    ModerationStateError,
)
from app.services.role_service import (
    RoleConfigurationError,
    RoleService,
    UserNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["administration"])
admin_dependency = require_role("admin")


def get_listing_moderation_service(
    db: Session = Depends(get_db),
) -> ListingModerationService:
    return ListingModerationService(db)


def _raise_moderation_http_error(
    error: Exception,
    listing_id: int | None = None,
) -> NoReturn:
    if isinstance(error, ModerationListingNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found.",
        ) from error
    if isinstance(error, ModerationStateError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    if isinstance(error, ModerationReasonRequiredError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    logger.exception("Listing moderation request failed for %s", listing_id)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Listing moderation is temporarily unavailable.",
    ) from error


@router.get(
    "/listings/pending",
    response_model=list[ListingResponse],
    dependencies=[Depends(admin_dependency)],
)
def list_pending_moderation(
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> list[ListingResponse]:
    try:
        return service.list_pending_listings()
    except SQLAlchemyError as exc:
        _raise_moderation_http_error(exc)


@router.get(
    "/listings/published",
    response_model=list[ListingResponse],
    dependencies=[Depends(admin_dependency)],
)
def list_published_listings(
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> list[ListingResponse]:
    try:
        return service.list_published_listings()
    except SQLAlchemyError as exc:
        _raise_moderation_http_error(exc)


@router.get(
    "/listings/{listing_id}/moderation-history",
    response_model=list[ListingModerationResponse],
    dependencies=[Depends(admin_dependency)],
)
def get_listing_moderation_history(
    listing_id: Annotated[int, Path(gt=0)],
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> list[ListingModerationResponse]:
    try:
        return service.get_moderation_history(listing_id)
    except (
        ModerationListingNotFoundError,
        ModerationStateError,
        ModerationReasonRequiredError,
        SQLAlchemyError,
    ) as exc:
        _raise_moderation_http_error(exc, listing_id)


@router.post(
    "/listings/{listing_id}/approve",
    response_model=ListingResponse,
)
def approve_listing(
    listing_id: Annotated[int, Path(gt=0)],
    request: ModerationApprovalRequest = Body(
        default=ModerationApprovalRequest(),
    ),
    current_admin: User = Depends(admin_dependency),
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> ListingResponse:
    try:
        return service.approve_listing(
            listing_id,
            current_admin.user_id,
            request.reason,
        )
    except (
        ModerationListingNotFoundError,
        ModerationStateError,
        ModerationReasonRequiredError,
        SQLAlchemyError,
    ) as exc:
        _raise_moderation_http_error(exc, listing_id)


@router.post(
    "/listings/{listing_id}/reject",
    response_model=ListingResponse,
)
def reject_listing(
    listing_id: Annotated[int, Path(gt=0)],
    request: ModerationReasonRequest,
    current_admin: User = Depends(admin_dependency),
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> ListingResponse:
    try:
        return service.reject_listing(
            listing_id,
            current_admin.user_id,
            request.reason,
        )
    except (
        ModerationListingNotFoundError,
        ModerationStateError,
        ModerationReasonRequiredError,
        SQLAlchemyError,
    ) as exc:
        _raise_moderation_http_error(exc, listing_id)


@router.post(
    "/listings/{listing_id}/hide",
    response_model=ListingResponse,
)
def hide_listing(
    listing_id: Annotated[int, Path(gt=0)],
    request: ModerationReasonRequest,
    current_admin: User = Depends(admin_dependency),
    service: ListingModerationService = Depends(
        get_listing_moderation_service,
    ),
) -> ListingResponse:
    try:
        return service.hide_listing(
            listing_id,
            current_admin.user_id,
            request.reason,
        )
    except (
        ModerationListingNotFoundError,
        ModerationStateError,
        ModerationReasonRequiredError,
        SQLAlchemyError,
    ) as exc:
        _raise_moderation_http_error(exc, listing_id)


@router.post(
    "/users/{user_id}/roles/landlord",
    response_model=LandlordRoleGrantResponse,
)
def grant_landlord_role(
    user_id: Annotated[int, Path(gt=0)],
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> LandlordRoleGrantResponse:
    if user_id == current_admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators cannot grant the landlord role to themselves.",
        )

    try:
        granted = RoleService(db).grant_landlord_role(
            target_user_id=user_id,
            granted_by_user_id=current_admin.user_id,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist.",
        ) from exc
    except RoleConfigurationError as exc:
        logger.exception("Landlord role grant is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role assignment is temporarily unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to grant landlord role")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role assignment is temporarily unavailable.",
        ) from exc

    return LandlordRoleGrantResponse(user_id=user_id, granted=granted)
