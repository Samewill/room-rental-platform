from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rental_interest_notification import RentalInterestNotification


class RentalInterestNotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user(
        self,
        user_id: int,
        *,
        limit: int = 100,
    ) -> list[RentalInterestNotification]:
        statement = (
            select(RentalInterestNotification)
            .where(
                RentalInterestNotification.recipient_user_id == user_id,
            )
            .order_by(
                RentalInterestNotification.created_at.desc(),
                RentalInterestNotification.notification_id.desc(),
            )
            .limit(limit)
        )
        return list(self._db.scalars(statement).all())

    def get_for_user(
        self,
        user_id: int,
        notification_id: int,
        *,
        for_update: bool = False,
    ) -> RentalInterestNotification | None:
        statement = select(RentalInterestNotification).where(
            RentalInterestNotification.notification_id == notification_id,
            RentalInterestNotification.recipient_user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update(
                of=RentalInterestNotification,
            )
        return self._db.scalar(statement)

    def get_next_pending_whatsapp(
        self,
    ) -> RentalInterestNotification | None:
        statement = (
            select(RentalInterestNotification)
            .where(
                RentalInterestNotification.whatsapp_delivery_status
                == "pending",
            )
            .order_by(
                RentalInterestNotification.created_at,
                RentalInterestNotification.notification_id,
            )
            .limit(1)
            .with_for_update(
                of=RentalInterestNotification,
                skip_locked=True,
            )
        )
        return self._db.scalar(statement)

    def list_stale_sending(
        self,
        stale_before: datetime,
    ) -> list[RentalInterestNotification]:
        statement = (
            select(RentalInterestNotification)
            .where(
                RentalInterestNotification.whatsapp_delivery_status
                == "sending",
                RentalInterestNotification.whatsapp_started_at <= stale_before,
            )
            .with_for_update(
                of=RentalInterestNotification,
                skip_locked=True,
            )
        )
        return list(self._db.scalars(statement).all())
