from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self._db.scalar(statement)

    def get_by_phone_no(self, phone_no: str) -> User | None:
        statement = select(User).where(User.phone_no == phone_no)
        return self._db.scalar(statement)

    def add(self, user: User) -> User:
        self._db.add(user)
        self._db.flush()
        return user
