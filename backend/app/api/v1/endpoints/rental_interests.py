import logging
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.amenity import AmenityName
from app.schemas.rental_interest import (
    InterestOpportunityRequest,
    InterestOpportunityResponse,
    RentalInterestCreateRequest,
    RentalInterestLandlordResponse,
    RentalInterestRenewRequest,
    RentalInterestStatusRequest,
    RentalInterestTenantResponse,
)
from app.services.rental_interest_service import (
    RentalInterestAmenityError,
    RentalInterestCapacityError,
    RentalInterestCapacityFullError,
    RentalInterestDuplicateError,
    RentalInterestForbiddenError,
    RentalInterestNotFoundError,
    RentalInterestOpportunityUnavailableError,
    RentalInterestRateLimitError,
    RentalInterestService,
    RentalInterestStateError,
    RentalInterestWaitlistConsentRequiredError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["rental interest"])
tenant_dependency = require_role("tenant")
landlord_dependency = require_role("landlord")

RoomTypeFilter = Literal[
    "single_room",
    "shared_room",
    "bachelor_flat",
    "self_contained",
]


def get_rental_interest_service(
    db: Session = Depends(get_db),
) -> RentalInterestService:
    return RentalInterestService(db)


@router.get(
    "/interest-opportunities",
    response_model=list[InterestOpportunityResponse],
)
def list_public_interest_opportunities(
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> list[InterestOpportunityResponse]:
    try:
        return service.list_public_opportunities()
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve public interest opportunities")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Future availability is temporarily unavailable.",
        ) from exc


@router.get(
    "/users/me/interest-opportunities",
    response_model=list[InterestOpportunityResponse],
)
def list_my_interest_opportunities(
    current_landlord: User = Depends(landlord_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> list[InterestOpportunityResponse]:
    try:
        return service.list_for_landlord(current_landlord.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve landlord interest opportunities")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Future availability is temporarily unavailable.",
        ) from exc


@router.put(
    "/listings/{listing_id}/interest-opportunity",
    response_model=InterestOpportunityResponse,
)
def save_interest_opportunity(
    changes: InterestOpportunityRequest,
    listing_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> InterestOpportunityResponse:
    try:
        return service.save_opportunity(
            current_landlord.user_id,
            listing_id,
            changes,
        )
    except RentalInterestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestOpportunityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RentalInterestCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to save interest opportunity for listing %s",
            listing_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Future availability could not be saved right now.",
        ) from exc


@router.post(
    "/interest-opportunities/{opportunity_id}/close",
    response_model=InterestOpportunityResponse,
)
def close_interest_opportunity(
    opportunity_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> InterestOpportunityResponse:
    try:
        return service.close_opportunity(
            current_landlord.user_id,
            opportunity_id,
        )
    except RentalInterestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to close interest opportunity %s",
            opportunity_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Future availability could not be closed right now.",
        ) from exc


@router.post(
    "/interest-opportunities/{opportunity_id}/interests",
    response_model=RentalInterestTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rental_interest(
    changes: RentalInterestCreateRequest,
    opportunity_id: Annotated[int, Path(gt=0)],
    current_tenant: User = Depends(tenant_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> RentalInterestTenantResponse:
    try:
        return service.create_interest(
            current_tenant.user_id,
            opportunity_id,
            changes,
        )
    except RentalInterestOpportunityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RentalInterestDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RentalInterestWaitlistConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "waitlist_consent_required",
                "message": str(exc),
            },
        ) from exc
    except RentalInterestCapacityFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "capacity_full",
                "message": str(exc),
            },
        ) from exc
    except RentalInterestRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except RentalInterestAmenityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to create rental interest for opportunity %s",
            opportunity_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interest could not be registered right now.",
        ) from exc


@router.get(
    "/users/me/rental-interests",
    response_model=list[RentalInterestTenantResponse],
)
def list_my_rental_interests(
    current_tenant: User = Depends(tenant_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> list[RentalInterestTenantResponse]:
    try:
        return service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve tenant rental interests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interests are temporarily unavailable.",
        ) from exc


@router.post(
    "/rental-interests/{interest_id}/withdraw",
    response_model=RentalInterestTenantResponse,
)
def withdraw_rental_interest(
    interest_id: Annotated[int, Path(gt=0)],
    current_tenant: User = Depends(tenant_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> RentalInterestTenantResponse:
    try:
        return service.withdraw_interest(
            current_tenant.user_id,
            interest_id,
        )
    except RentalInterestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RentalInterestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to withdraw rental interest %s", interest_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interest could not be withdrawn right now.",
        ) from exc


@router.post(
    "/rental-interests/{interest_id}/renew",
    response_model=RentalInterestTenantResponse,
)
def renew_rental_interest(
    interest_id: Annotated[int, Path(gt=0)],
    changes: RentalInterestRenewRequest = RentalInterestRenewRequest(),
    current_tenant: User = Depends(tenant_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> RentalInterestTenantResponse:
    try:
        return service.renew_interest(
            current_tenant.user_id,
            interest_id,
            join_waitlist=changes.join_waitlist,
        )
    except RentalInterestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RentalInterestOpportunityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RentalInterestRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except RentalInterestWaitlistConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "waitlist_consent_required",
                "message": str(exc),
            },
        ) from exc
    except RentalInterestCapacityFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "capacity_full",
                "message": str(exc),
            },
        ) from exc
    except RentalInterestDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RentalInterestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to renew rental interest %s", interest_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interest could not be renewed right now.",
        ) from exc


@router.get(
    "/users/me/received-rental-interests",
    response_model=list[RentalInterestLandlordResponse],
)
def list_received_rental_interests(
    opportunity_id: int | None = Query(default=None, gt=0),
    move_in_from: date | None = None,
    move_in_until: date | None = None,
    minimum_budget: Decimal | None = Query(default=None, gt=0),
    maximum_budget: Decimal | None = Query(default=None, gt=0),
    preferred_room_type: RoomTypeFilter | None = None,
    required_amenities: Annotated[list[AmenityName] | None, Query()] = None,
    current_landlord: User = Depends(landlord_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> list[RentalInterestLandlordResponse]:
    if (
        move_in_from is not None
        and move_in_until is not None
        and move_in_from > move_in_until
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="move_in_from cannot be after move_in_until.",
        )
    if (
        minimum_budget is not None
        and maximum_budget is not None
        and minimum_budget > maximum_budget
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="minimum_budget cannot exceed maximum_budget.",
        )
    try:
        return service.list_for_landlord_interests(
            current_landlord.user_id,
            opportunity_id=opportunity_id,
            move_in_from=move_in_from,
            move_in_until=move_in_until,
            minimum_budget=minimum_budget,
            maximum_budget=maximum_budget,
            preferred_room_type=preferred_room_type,
            required_amenities=required_amenities,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve landlord rental interests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interests are temporarily unavailable.",
        ) from exc


@router.patch(
    "/rental-interests/{interest_id}/status",
    response_model=RentalInterestLandlordResponse,
)
def update_rental_interest_status(
    changes: RentalInterestStatusRequest,
    interest_id: Annotated[int, Path(gt=0)],
    current_landlord: User = Depends(landlord_dependency),
    service: RentalInterestService = Depends(get_rental_interest_service),
) -> RentalInterestLandlordResponse:
    try:
        return service.update_status(
            current_landlord.user_id,
            interest_id,
            changes.status,
        )
    except RentalInterestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RentalInterestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RentalInterestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RentalInterestOpportunityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to update rental interest status %s",
            interest_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rental interest could not be updated right now.",
        ) from exc
