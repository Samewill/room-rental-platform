from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class AccountAlreadyExistsError(Exception):
    pass


class RoleConfigurationError(Exception):
    pass


class AuthService:
    UNIQUE_USER_CONSTRAINTS = {"users_email_key", "users_phone_no_key"}

    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._roles = RoleRepository(db)

    def register(self, request: RegisterRequest) -> User:
        email = str(request.email).casefold()
        phone_no = request.phone_no

        if (
            self._users.get_by_email(email) is not None
            or self._users.get_by_phone_no(phone_no) is not None
        ):
            raise AccountAlreadyExistsError(
                "An account with these details already exists."
            )

        selected_role = self._roles.get_by_name(request.role)
        if selected_role is None:
            self._db.rollback()
            raise RoleConfigurationError(
                f"The {request.role} role is not configured."
            )

        user = User(
            full_name=request.full_name,
            phone_no=phone_no,
            email=email,
            password_hash=hash_password(request.password.get_secret_value()),
            business_name=request.business_name,
        )

        try:
            self._users.add(user)
            self._roles.assign_to_user(user.user_id, selected_role.role_id)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name in self.UNIQUE_USER_CONSTRAINTS:
                raise AccountAlreadyExistsError(
                    "An account with these details already exists."
                ) from exc
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return user

    def authenticate(self, request: LoginRequest) -> User | None:
        email = str(request.email).casefold()
        user = self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            return None

        if not verify_password(
            request.password.get_secret_value(),
            user.password_hash,
        ):
            return None

        return user
