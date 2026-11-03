import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.review import ReviewCreateRequest, ReviewResponse
from app.services.review_service import (
    ReviewAlreadyExistsError,
    ReviewContactRequestNotFoundError,
    ReviewEligibilityError,
    ReviewService,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["reviews"])
tenant_dependency = require_role("tenant")


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    return ReviewService(db)


@router.get(
    "/me/reviews",
    response_model=list[ReviewResponse],
)
def list_my_reviews(
    current_tenant: User = Depends(tenant_dependency),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewResponse]:
    try:
        reviews = service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve tenant reviews")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Your reviews are temporarily unavailable.",
        ) from exc

    return [
        ReviewResponse.model_validate(review)
        for review in reviews
    ]


@router.post(
    "/me/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    request: ReviewCreateRequest,
    current_tenant: User = Depends(tenant_dependency),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    try:
        review = service.create_for_tenant(current_tenant.user_id, request)
    except ReviewContactRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReviewEligibilityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ReviewAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to create review for contact request %s", request.contact_request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review could not be submitted right now.",
        ) from exc

    return ReviewResponse.model_validate(review)
