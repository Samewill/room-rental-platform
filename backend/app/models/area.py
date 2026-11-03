from sqlalchemy import BigInteger, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("name", name="areas_name_key"),)

    area_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
