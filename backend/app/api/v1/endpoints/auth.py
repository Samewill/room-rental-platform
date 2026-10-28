import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import (
    AccountAlreadyExistsError,
    AuthService,
    RoleConfigurationError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        user = AuthService(db).register(request)
    except AccountAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RoleConfigurationError as exc:
        logger.exception("Registration is unavailable because a role is missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Registration failed because of a database error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable.",
        ) from exc

    return UserResponse.model_validate(user).model_copy(
        update={"roles": [AuthService.TENANT_ROLE]},
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = AuthService(db).authenticate(request)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Login failed because of a database error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login is temporarily unavailable.",
        ) from exc
    except RuntimeError as exc:
        logger.exception("Login token configuration is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login is temporarily unavailable.",
        ) from exc

    return TokenResponse(
        access_token=access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )
