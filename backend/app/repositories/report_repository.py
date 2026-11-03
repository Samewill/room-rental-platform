from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report, ReportHistory


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, report: Report) -> Report:
        self._db.add(report)
        self._db.flush()
        return report

    def add_history(
        self,
        report_id: int,
        actor_user_id: int,
        action: str,
        note: str | None = None,
    ) -> ReportHistory:
        history = ReportHistory(
            report_id=report_id,
            actor_user_id=actor_user_id,
            action=action,
            note=note,
        )
        self._db.add(history)
        self._db.flush()
        return history

    def list_for_tenant(self, tenant_id: int) -> list[Report]:
        statement = (
            select(Report)
            .where(Report.tenant_id == tenant_id)
            .order_by(Report.created_at.desc(), Report.report_id.desc())
        )
        return list(self._db.scalars(statement).all())

    def list_for_admin(
        self,
        status_filter: str | None = None,
    ) -> list[Report]:
        statement = select(Report)
        if status_filter is not None:
            statement = statement.where(Report.status == status_filter)
        statement = statement.order_by(
            Report.created_at.desc(),
            Report.report_id.desc(),
        )
        return list(self._db.scalars(statement).all())

    def get_by_id(
        self,
        report_id: int,
        *,
        for_update: bool = False,
    ) -> Report | None:
        statement = select(Report).where(Report.report_id == report_id)
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def list_history(self, report_id: int) -> list[ReportHistory]:
        statement = (
            select(ReportHistory)
            .where(ReportHistory.report_id == report_id)
            .order_by(ReportHistory.created_at, ReportHistory.history_id)
        )
        return list(self._db.scalars(statement).all())
