import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.whatsapp import WhatsAppContact
from app.services.rental_interest_notification_service import (
    RentalInterestNotificationNotFoundError,
    RentalInterestNotificationService,
)


class RentalInterestNotificationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.provider = Mock()
        self.service = RentalInterestNotificationService(
            self.db,
            self.provider,
        )
        self.service._notifications = Mock()
        self.service._notifications.list_stale_sending.return_value = []

    @staticmethod
    def make_notification(
        *,
        created_at: datetime | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            notification_id=10,
            recipient_user_id=6,
            interest_id=42,
            listing_id=14,
            event_key="rental-interest:42:history:3",
            event_type="interest_status_updated",
            title="Your interest was updated",
            body="The landlord updated your rental interest.",
            read_at=None,
            created_at=created_at or datetime(2026, 11, 12, 12),
            whatsapp_delivery_status="pending",
            provider_message_id=None,
            last_error=None,
            sent_at=None,
        )

    def test_notification_read_is_scoped_to_the_recipient(self) -> None:
        self.service._notifications.get_for_user.return_value = None

        with self.assertRaises(RentalInterestNotificationNotFoundError):
            self.service.mark_read(user_id=6, notification_id=10)

        self.service._notifications.get_for_user.assert_called_once_with(
            6,
            10,
            for_update=True,
        )
        self.db.commit.assert_not_called()

    def test_mark_read_is_idempotent(self) -> None:
        notification = self.make_notification()
        self.service._notifications.get_for_user.return_value = notification

        first_result = self.service.mark_read(user_id=6, notification_id=10)
        first_read_at = first_result.read_at
        second_result = self.service.mark_read(user_id=6, notification_id=10)

        self.assertIsNotNone(first_read_at)
        self.assertEqual(second_result.read_at, first_read_at)
        self.db.commit.assert_called_once()

    def test_unsubscribed_contact_is_not_sent_a_whatsapp_notification(self) -> None:
        notification = self.make_notification()
        self.service._notifications.get_next_pending_whatsapp.side_effect = [
            notification,
            None,
        ]
        self.db.get.return_value = None

        sent_count = self.service.deliver_pending_whatsapp()

        self.assertEqual(sent_count, 0)
        self.assertEqual(notification.whatsapp_delivery_status, "skipped")
        self.provider.send_template.assert_not_called()

    def test_whatsapp_is_sent_only_with_current_opt_in_and_phone_redaction(
        self,
    ) -> None:
        created_at = datetime(2026, 11, 12, 12)
        notification = self.make_notification(created_at=created_at)
        notification.title = "Your room at +27123456789 was updated"
        notification.body = "Contact at +27123456789"
        self.service._notifications.get_next_pending_whatsapp.side_effect = [
            notification,
            None,
        ]
        self.db.get.return_value = WhatsAppContact(
            user_id=6,
            encrypted_phone="encrypted",
            phone_lookup_hash="lookup",
            verified_at=created_at - timedelta(days=1),
            opted_in_at=created_at - timedelta(hours=1),
            opted_out_at=None,
        )
        self.provider.send_template.return_value = "wamid.123"

        with (
            patch(
                "app.services.rental_interest_notification_service."
                "decrypt_phone_number",
                return_value="+27111111111",
            ),
            patch(
                "app.services.rental_interest_notification_service."
                "get_settings",
                return_value=SimpleNamespace(
                    whatsapp_message_template_name="rental_message_notification",
                ),
            ),
        ):
            sent_count = self.service.deliver_pending_whatsapp()

        self.assertEqual(sent_count, 1)
        self.assertEqual(notification.whatsapp_delivery_status, "sent")
        self.assertEqual(notification.provider_message_id, "wamid.123")
        self.provider.send_template.assert_called_once()
        message = self.provider.send_template.call_args.args[2]
        self.assertNotIn("+27123456789", message)
        self.assertIn("[phone number removed]", message)
        self.assertIn("Reply STOP", message)

    def test_opt_in_after_notification_does_not_send_old_notification(self) -> None:
        notification = self.make_notification(
            created_at=datetime(2026, 11, 12, 12),
        )
        self.service._notifications.get_next_pending_whatsapp.side_effect = [
            notification,
            None,
        ]
        self.db.get.return_value = WhatsAppContact(
            user_id=6,
            encrypted_phone="encrypted",
            phone_lookup_hash="lookup",
            verified_at=datetime(2026, 11, 13),
            opted_in_at=datetime(2026, 11, 13),
            opted_out_at=None,
        )

        sent_count = self.service.deliver_pending_whatsapp()

        self.assertEqual(sent_count, 0)
        self.assertEqual(notification.whatsapp_delivery_status, "skipped")
        self.provider.send_template.assert_not_called()

    def test_interrupted_delivery_is_recorded_and_not_resent(self) -> None:
        notification = self.make_notification()
        notification.whatsapp_delivery_status = "sending"
        notification.whatsapp_started_at = datetime(2026, 11, 12, 12)
        self.service._notifications.list_stale_sending.return_value = [
            notification,
        ]
        self.service._notifications.get_next_pending_whatsapp.return_value = None

        sent_count = self.service.deliver_pending_whatsapp()

        self.assertEqual(sent_count, 0)
        self.assertEqual(notification.whatsapp_delivery_status, "failed")
        self.assertIn("interrupted", notification.last_error)
        self.provider.send_template.assert_not_called()


if __name__ == "__main__":
    unittest.main()
