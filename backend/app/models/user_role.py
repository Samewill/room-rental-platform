from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="user_roles_user_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "roles.role_id",
            name="user_roles_role_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
