import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.saved_search import (
    SavedSearchCreateRequest,
    SavedSearchResponse,
)
from app.services.saved_search_service import (
    SavedSearchAmenityNotFoundError,
    SavedSearchService,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["saved searches"])
tenant_dependency = require_role("tenant")


def get_saved_search_service(
    db: Session = Depends(get_db),
) -> SavedSearchService:
    return SavedSearchService(db)


@router.post(
    "/me/saved-searches",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_search(
    request: SavedSearchCreateRequest,
    current_tenant: User = Depends(tenant_dependency),
    service: SavedSearchService = Depends(get_saved_search_service),
) -> SavedSearchResponse:
    try:
        saved_search = service.create_for_tenant(
            current_tenant.user_id,
            request,
        )
    except SavedSearchAmenityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to create saved search")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved search could not be created right now.",
        ) from exc

    return SavedSearchResponse.model_validate(saved_search)


@router.get(
    "/me/saved-searches",
    response_model=list[SavedSearchResponse],
)
def list_my_saved_searches(
    current_tenant: User = Depends(tenant_dependency),
    service: SavedSearchService = Depends(get_saved_search_service),
) -> list[SavedSearchResponse]:
    try:
        saved_searches = service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve tenant saved searches")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved searches are temporarily unavailable.",
        ) from exc

    return [
        SavedSearchResponse.model_validate(saved_search)
        for saved_search in saved_searches
    ]


@router.delete(
    "/me/saved-searches/{saved_search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_saved_search(
    saved_search_id: int,
    current_tenant: User = Depends(tenant_dependency),
    service: SavedSearchService = Depends(get_saved_search_service),
) -> None:
    try:
        deleted = service.delete_for_tenant(
            current_tenant.user_id,
            saved_search_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to delete tenant saved search")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved search could not be deleted right now.",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search does not exist.",
        )
