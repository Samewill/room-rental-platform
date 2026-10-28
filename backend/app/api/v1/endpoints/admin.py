import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import LandlordRoleGrantResponse
from app.services.role_service import (
    RoleConfigurationError,
    RoleService,
    UserNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["administration"])


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
