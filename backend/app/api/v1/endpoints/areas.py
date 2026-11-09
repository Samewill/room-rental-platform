import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.area_repository import AreaRepository
from app.schemas.area import AreaResolveRequest, AreaResponse
from app.services.area_service import AreaService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/areas", tags=["areas"])


def get_area_service(db: Session = Depends(get_db)) -> AreaService:
    return AreaService(AreaRepository(db))


@router.get("", response_model=list[AreaResponse])
def list_areas(
    search: str | None = Query(default=None, min_length=1, max_length=150),
    limit: int = Query(default=10, ge=1, le=25),
    service: AreaService = Depends(get_area_service),
) -> list[AreaResponse]:
    if search is not None and not search.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Area search must contain non-whitespace characters.",
        )

    try:
        if search is None:
            return service.list_areas()
        return service.search_areas(search.strip(), limit)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve areas")
        raise HTTPException(
            status_code=503,
            detail="Area data is temporarily unavailable.",
        ) from exc


@router.post(
    "/resolve",
    response_model=AreaResponse,
    status_code=status.HTTP_200_OK,
)
def resolve_area(
    changes: AreaResolveRequest,
    _current_landlord: User = Depends(require_role("landlord")),
    service: AreaService = Depends(get_area_service),
) -> AreaResponse:
    try:
        return service.resolve_area(changes.name)
    except SQLAlchemyError as exc:
        logger.exception("Failed to resolve landlord area")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Area data is temporarily unavailable.",
        ) from exc
