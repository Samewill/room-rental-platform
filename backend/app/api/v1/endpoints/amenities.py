import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.amenity_repository import AmenityRepository
from app.schemas.amenity import AmenityResponse
from app.services.amenity_service import AmenityService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/amenities", tags=["amenities"])


def get_amenity_service(
    db: Session = Depends(get_db),
) -> AmenityService:
    return AmenityService(AmenityRepository(db))


@router.get("", response_model=list[AmenityResponse])
def list_amenities(
    service: AmenityService = Depends(get_amenity_service),
) -> list[AmenityResponse]:
    try:
        return service.list_amenities()
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve amenities")
        raise HTTPException(
            status_code=503,
            detail="Amenity data is temporarily unavailable.",
        ) from exc
