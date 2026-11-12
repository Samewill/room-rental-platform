import logging

from app.db.session import get_session_factory
from app.services.rental_interest_service import RentalInterestService
from app.services.rental_interest_notification_service import (
    RentalInterestNotificationService,
)


logger = logging.getLogger(__name__)


def main() -> None:
    with get_session_factory()() as db:
        expired_count = RentalInterestService(db).expire_due_interests()
        whatsapp_count = RentalInterestNotificationService(
            db,
        ).deliver_pending_whatsapp()
    logger.info(
        "Rental interest maintenance completed",
        extra={
            "expired_interest_count": expired_count,
            "whatsapp_notification_count": whatsapp_count,
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
