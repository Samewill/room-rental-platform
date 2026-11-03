from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user_role import UserRole


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_name(self, name: str) -> Role | None:
        statement = select(Role).where(Role.name == name)
        return self._db.scalar(statement)

    def list_for_user(self, user_id: int) -> list[Role]:
        statement = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.role_id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        return list(self._db.scalars(statement).all())

    def assign_to_user(self, user_id: int, role_id: int) -> UserRole:
        assignment = UserRole(user_id=user_id, role_id=role_id)
        self._db.add(assignment)
        self._db.flush()
        return assignment
