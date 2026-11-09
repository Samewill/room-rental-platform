from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.area import Area


class AreaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, area_id: int) -> Area | None:
        return self._db.get(Area, area_id)

    def get_by_name(self, name: str) -> Area | None:
        statement = select(Area).where(
            func.lower(Area.name) == name.lower(),
        )
        return self._db.scalar(statement)

    def list_all(self) -> list[Area]:
        statement = select(Area).order_by(Area.name, Area.area_id)
        return list(self._db.scalars(statement).all())

    def search_by_name(self, name: str, limit: int) -> list[Area]:
        statement = (
            select(Area)
            .where(Area.name.ilike(f"%{name}%"))
            .order_by(Area.name, Area.area_id)
            .limit(limit)
        )
        return list(self._db.scalars(statement).all())

    def get_or_create(self, name: str) -> Area:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing

        area = Area(name=name)
        self._db.add(area)
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            existing = self.get_by_name(name)
            if existing is None:
                raise
            return existing
        return area
