import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.rental_interest_notification import (
    RentalInterestNotificationResponse,
)
from app.services.rental_interest_notification_service import (
    RentalInterestNotificationNotFoundError,
    RentalInterestNotificationService,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["rental interest notifications"])


def get_rental_interest_notification_service(
    db: Session = Depends(get_db),
) -> RentalInterestNotificationService:
    return RentalInterestNotificationService(db)


@router.get(
    "/users/me/rental-interest-notifications",
    response_model=list[RentalInterestNotificationResponse],
)
def list_my_rental_interest_notifications(
    current_user: User = Depends(get_current_user),
    service: RentalInterestNotificationService = Depends(
        get_rental_interest_notification_service,
    ),
) -> list[RentalInterestNotificationResponse]:
    try:
        return service.list_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Rental-interest notifications could not be loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notifications are temporarily unavailable.",
        ) from exc


@router.patch(
    "/users/me/rental-interest-notifications/{notification_id}/read",
    response_model=RentalInterestNotificationResponse,
)
def mark_rental_interest_notification_read(
    notification_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: RentalInterestNotificationService = Depends(
        get_rental_interest_notification_service,
    ),
) -> RentalInterestNotificationResponse:
    try:
        return service.mark_read(current_user.user_id, notification_id)
    except RentalInterestNotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Rental-interest notification %s could not be marked read",
            notification_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The notification could not be updated right now.",
        ) from exc
