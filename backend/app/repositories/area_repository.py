from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.area import Area


class AreaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, area_id: int) -> Area | None:
        return self._db.get(Area, area_id)

    def list_all(self) -> list[Area]:
        statement = select(Area).order_by(Area.name, Area.area_id)
        return list(self._db.scalars(statement).all())
