import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.contact_request import ContactRequest
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.contact_request import (
    ContactRequestResponse,
    ContactRequestStatusUpdate,
)
from app.services.contact_request_service import (
    ContactRequestForbiddenError,
    ContactRequestListingUnavailableError,
    ContactRequestNotFoundError,
    ContactRequestService,
    ContactRequestStateError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["contact requests"])
tenant_dependency = require_role("tenant")
landlord_dependency = require_role("landlord")


def get_contact_request_service(
    db: Session = Depends(get_db),
) -> ContactRequestService:
    return ContactRequestService(db)


@router.get(
    "/users/me/contact-requests",
    response_model=list[ContactRequestResponse],
)
def list_my_contact_requests(
    current_tenant: User = Depends(tenant_dependency),
    service: ContactRequestService = Depends(get_contact_request_service),
) -> list[ContactRequestResponse]:
    try:
        requests = service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve tenant contact requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contact requests are temporarily unavailable.",
        ) from exc

    return [
        ContactRequestResponse.model_validate(contact_request)
        for contact_request in requests
    ]


@router.get(
    "/users/me/received-requests",
    response_model=list[ContactRequestResponse],
)
def list_received_contact_requests(
    current_landlord: User = Depends(landlord_dependency),
    service: ContactRequestService = Depends(get_contact_request_service),
) -> list[ContactRequestResponse]:
    try:
        requests = service.list_for_landlord(current_landlord.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve landlord contact requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contact requests are temporarily unavailable.",
        ) from exc

    return [
        ContactRequestResponse.model_validate(contact_request)
        for contact_request in requests
    ]


@router.post(
    "/listings/{listing_id}/contact-requests",
    response_model=ContactRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact_request(
    listing_id: Annotated[int, Path(gt=0)],
    current_tenant: User = Depends(tenant_dependency),
    service: ContactRequestService = Depends(get_contact_request_service),
) -> ContactRequestResponse:
    try:
        contact_request = service.create_request(
            current_tenant.user_id,
            listing_id,
        )
    except ContactRequestListingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found or unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to create contact request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contact request could not be created right now.",
        ) from exc

    return ContactRequestResponse.model_validate(contact_request)


@router.patch(
    "/contact-requests/{request_id}",
    response_model=ContactRequestResponse,
)
def update_contact_request_status(
    changes: ContactRequestStatusUpdate,
    request_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ContactRequestService = Depends(get_contact_request_service),
) -> ContactRequestResponse:
    required_role = (
        "tenant" if changes.status == "cancelled" else "landlord"
    )
    try:
        roles = RoleRepository(db).list_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to check contact request update permissions")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contact request could not be updated right now.",
        ) from exc

    if not any(role.name == required_role for role in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    try:
        contact_request = service.update_status(
            current_user.user_id,
            request_id,
            changes.status,
        )
    except ContactRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact request not found.",
        ) from exc
    except ContactRequestForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ContactRequestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to update contact request %s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contact request could not be updated right now.",
        ) from exc

    return ContactRequestResponse.model_validate(contact_request)
