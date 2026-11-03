from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserProfileUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def update_profile(
        self,
        user: User,
        changes: UserProfileUpdate,
    ) -> User:
        for field_name, value in changes.model_dump(exclude_unset=True).items():
            setattr(user, field_name, value)

        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return user
