import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.area_repository import AreaRepository
from app.schemas.area import AreaResponse
from app.services.area_service import AreaService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/areas", tags=["areas"])


def get_area_service(db: Session = Depends(get_db)) -> AreaService:
    return AreaService(AreaRepository(db))


@router.get("", response_model=list[AreaResponse])
def list_areas(
    service: AreaService = Depends(get_area_service),
) -> list[AreaResponse]:
    try:
        return service.list_areas()
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve areas")
        raise HTTPException(
            status_code=503,
            detail="Area data is temporarily unavailable.",
        ) from exc
