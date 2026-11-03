from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.amenity import Amenity


class AmenityRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Amenity]:
        statement = select(Amenity).order_by(Amenity.name, Amenity.amenity_id)
        return list(self._db.scalars(statement).all())

    def get_by_names(self, names: list[str]) -> list[Amenity]:
        if not names:
            return []
        statement = select(Amenity).where(Amenity.name.in_(names))
        return list(self._db.scalars(statement).all())
