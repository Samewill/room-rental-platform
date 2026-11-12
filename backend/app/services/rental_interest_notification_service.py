import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.whatsapp_privacy import (
    decrypt_phone_number,
    redact_phone_numbers,
)
from app.models.rental_interest_notification import RentalInterestNotification
from app.models.whatsapp import WhatsAppContact
from app.repositories.rental_interest_notification_repository import (
    RentalInterestNotificationRepository,
)
from app.services.whatsapp_provider import (
    WhatsAppCloudAPI,
    WhatsAppProviderError,
)


logger = logging.getLogger(__name__)


class RentalInterestNotificationNotFoundError(Exception):
    pass


class RentalInterestNotificationService:
    def __init__(
        self,
        db: Session,
        provider: WhatsAppCloudAPI | None = None,
    ) -> None:
        self._db = db
        self._notifications = RentalInterestNotificationRepository(db)
        self._provider = provider or WhatsAppCloudAPI()

    def list_for_user(
        self,
        user_id: int,
    ) -> list[RentalInterestNotification]:
        return self._notifications.list_for_user(user_id)

    def mark_read(
        self,
        user_id: int,
        notification_id: int,
    ) -> RentalInterestNotification:
        notification = self._notifications.get_for_user(
            user_id,
            notification_id,
            for_update=True,
        )
        if notification is None:
            raise RentalInterestNotificationNotFoundError(
                "Notification does not exist.",
            )
        if notification.read_at is None:
            notification.read_at = self._now()
            self._commit()
        return notification

    def deliver_pending_whatsapp(self, *, limit: int = 100) -> int:
        stale_sending = self._notifications.list_stale_sending(
            self._now() - timedelta(minutes=30),
        )
        for notification in stale_sending:
            notification.whatsapp_delivery_status = "failed"
            notification.last_error = (
                "Delivery was interrupted before completion."
            )
        if stale_sending:
            self._commit()
            logger.error(
                "Marked %s interrupted rental-interest WhatsApp deliveries "
                "as failed",
                len(stale_sending),
            )

        sent_count = 0
        for _ in range(limit):
            notification = self._notifications.get_next_pending_whatsapp()
            if notification is None:
                break
            notification.whatsapp_delivery_status = "sending"
            notification.whatsapp_started_at = self._now()
            self._commit()
            contact = self._db.get(
                WhatsAppContact,
                notification.recipient_user_id,
            )
            if not self._is_enabled_for_notification(contact, notification):
                notification.whatsapp_delivery_status = "skipped"
                self._commit()
                continue

            try:
                assert contact is not None
                phone_number = decrypt_phone_number(contact.encrypted_phone)
                message = redact_phone_numbers(
                    f"{notification.title}: {notification.body} "
                    "Reply STOP to turn off WhatsApp updates.",
                )
                provider_message_id = self._provider.send_template(
                    phone_number,
                    get_settings().whatsapp_message_template_name,
                    message,
                )
            except (RuntimeError, WhatsAppProviderError) as exc:
                notification.whatsapp_delivery_status = "failed"
                notification.last_error = str(exc)[:255]
                self._commit()
                logger.exception(
                    "WhatsApp rental-interest notification %s failed",
                    notification.notification_id,
                )
                continue

            notification.whatsapp_delivery_status = "sent"
            notification.provider_message_id = provider_message_id
            notification.sent_at = self._now()
            notification.last_error = None
            self._commit()
            sent_count += 1
        return sent_count

    def _commit(self) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    @staticmethod
    def _is_enabled_for_notification(
        contact: WhatsAppContact | None,
        notification: RentalInterestNotification,
    ) -> bool:
        return (
            contact is not None
            and contact.verified_at is not None
            and contact.opted_in_at is not None
            and contact.opted_in_at <= notification.created_at
            and contact.opted_out_at is None
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
