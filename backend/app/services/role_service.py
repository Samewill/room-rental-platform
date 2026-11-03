import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    pass


class RoleConfigurationError(Exception):
    pass


class RoleService:
    LANDLORD_ROLE = "landlord"
    ROLE_ASSIGNMENT_CONSTRAINT = "user_roles_pkey"

    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._roles = RoleRepository(db)

    def grant_landlord_role(
        self,
        target_user_id: int,
        granted_by_user_id: int,
    ) -> bool:
        if self._users.get_by_id(target_user_id) is None:
            raise UserNotFoundError("User does not exist.")

        landlord_role = self._roles.get_by_name(self.LANDLORD_ROLE)
        if landlord_role is None:
            self._db.rollback()
            raise RoleConfigurationError("The landlord role is not configured.")

        current_roles = self._roles.list_for_user(target_user_id)
        if any(role.name == self.LANDLORD_ROLE for role in current_roles):
            return False

        try:
            self._roles.assign_to_user(target_user_id, landlord_role.role_id)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if (
                constraint_name == self.ROLE_ASSIGNMENT_CONSTRAINT
                and any(
                    role.name == self.LANDLORD_ROLE
                    for role in self._roles.list_for_user(target_user_id)
                )
            ):
                return False
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise

        logger.info(
            "Granted landlord role",
            extra={
                "granted_by_user_id": granted_by_user_id,
                "target_user_id": target_user_id,
            },
        )
        return True
