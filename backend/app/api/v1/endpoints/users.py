import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.user import UserProfileUpdate, UserResponse
from app.services.user_service import UserService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        roles = RoleRepository(db).list_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve user roles")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile data is temporarily unavailable.",
        ) from exc

    return UserResponse.model_validate(current_user).model_copy(
        update={"roles": [role.name for role in roles]},
    )


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    changes: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        user = UserService(db).update_profile(current_user, changes)
    except SQLAlchemyError as exc:
        logger.exception("Failed to update user profile")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile update is temporarily unavailable.",
        ) from exc

    try:
        roles = RoleRepository(db).list_for_user(user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve user roles after profile update")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile data is temporarily unavailable.",
        ) from exc

    return UserResponse.model_validate(user).model_copy(
        update={"roles": [role.name for role in roles]},
    )
