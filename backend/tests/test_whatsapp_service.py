import hashlib
import hmac
import unittest
import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import SecretStr
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import app.main
from app.core.whatsapp_privacy import encrypt_phone_number, phone_lookup_hash
from app.db.base import Base
from app.models.conversation import Conversation
from app.models.conversation import ConversationParticipant, Message
from app.models.user import User
from app.models.whatsapp import WhatsAppContact, WhatsAppMessage
from app.services.whatsapp_service import (
    WhatsAppService,
    WhatsAppVerificationError,
)


def make_settings() -> SimpleNamespace:
    encryption_key = base64.urlsafe_b64encode(b"e" * 32).decode("ascii")
    return SimpleNamespace(
        whatsapp_app_secret=SecretStr("test-app-secret"),
        whatsapp_verify_token=SecretStr("test-verify-token"),
        whatsapp_phone_encryption_key=SecretStr(encryption_key),
        whatsapp_phone_lookup_key=SecretStr("l" * 32),
        whatsapp_verification_template_name="phone_verify",
        whatsapp_message_template_name="message_notice",
        whatsapp_template_language="en_US",
    )


class WhatsAppServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = WhatsAppService(self.db, provider=Mock())

    def test_webhook_signature_requires_valid_hmac(self) -> None:
        body = b'{"object":"whatsapp_business_account"}'
        signature = "sha256=" + hmac.new(
            b"test-app-secret",
            body,
            hashlib.sha256,
        ).hexdigest()

        with (
            patch(
                "app.services.whatsapp_service.get_settings",
                return_value=make_settings(),
            ),
            patch(
                "app.core.whatsapp_privacy.get_settings",
                return_value=make_settings(),
            ),
        ):
            self.assertTrue(
                self.service.verify_webhook_signature(body, signature),
            )
            self.assertFalse(
                self.service.verify_webhook_signature(body, "sha256=invalid"),
            )
            self.assertFalse(
                self.service.verify_webhook_signature(body, None),
            )

    def test_webhook_challenge_checks_mode_and_token(self) -> None:
        with patch(
            "app.services.whatsapp_service.get_settings",
            return_value=make_settings(),
        ):
            self.assertTrue(
                self.service.verify_webhook_challenge(
                    "subscribe",
                    "test-verify-token",
                ),
            )
            self.assertFalse(
                self.service.verify_webhook_challenge(
                    "subscribe",
                    "wrong-token",
                ),
            )
            self.assertFalse(
                self.service.verify_webhook_challenge(
                    "other",
                    "test-verify-token",
                ),
            )

    def test_reply_context_routes_only_to_recipient_user(self) -> None:
        outbound = WhatsAppMessage(
            provider_message_id="wamid.outbound",
            conversation_id=28,
            recipient_user_id=7,
            direction="outbound",
            delivery_status="sent",
        )
        conversation = Conversation(
            conversation_id=28,
            contact_request_id=51,
        )
        self.db.scalar.return_value = outbound
        self.service._participant_conversation = Mock(
            return_value=conversation,
        )

        result = self.service._resolve_conversation(
            7,
            {"context": {"id": "wamid.outbound"}},
            "A reply",
            "+27123456789",
        )

        self.assertEqual(result, (conversation, "A reply"))
        self.service._participant_conversation.assert_called_once_with(28, 7)

    def test_reply_context_does_not_authorize_another_user(self) -> None:
        self.db.scalar.return_value = None
        self.service._participant_conversations = Mock(
            return_value=[
                Conversation(conversation_id=29, contact_request_id=52),
            ],
        )
        self.service._participant_conversation = Mock()

        result = self.service._resolve_conversation(
            99,
            {"context": {"id": "wamid.outbound"}},
            "A reply",
            "+27123456789",
        )

        self.assertEqual(result, (None, "A reply"))
        self.service._participant_conversation.assert_not_called()
        self.service._participant_conversations.assert_not_called()

    def test_inbound_webhook_is_saved_once_and_forwarded(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine, expire_on_commit=False)
        identifiers = {"message": 100, "whatsapp": 100}

        def assign_message_id(mapper: object, connection: object, target: Message) -> None:
            if target.message_id is None:
                identifiers["message"] += 1
                target.message_id = identifiers["message"]

        def assign_whatsapp_id(
            mapper: object,
            connection: object,
            target: WhatsAppMessage,
        ) -> None:
            if target.whatsapp_message_id is None:
                identifiers["whatsapp"] += 1
                target.whatsapp_message_id = identifiers["whatsapp"]

        event.listen(Message, "before_insert", assign_message_id)
        event.listen(WhatsAppMessage, "before_insert", assign_whatsapp_id)
        try:
            now = datetime(2026, 11, 5, 9)
            db.add_all(
                [
                    User(
                        user_id=7,
                        full_name="Tenant",
                        phone_no="private-tenant-phone",
                        email="tenant@example.com",
                        created_at=now,
                    ),
                    User(
                        user_id=8,
                        full_name="Landlord",
                        phone_no="private-landlord-phone",
                        email="landlord@example.com",
                        created_at=now,
                    ),
                ],
            )
            conversation = Conversation(
                conversation_id=28,
                contact_request_id=51,
                created_at=now,
            )
            db.add_all(
                [
                    conversation,
                    ConversationParticipant(
                        conversation_id=28,
                        user_id=7,
                    ),
                    ConversationParticipant(
                        conversation_id=28,
                        user_id=8,
                    ),
                ],
            )
            with patch(
                "app.core.whatsapp_privacy.get_settings",
                return_value=make_settings(),
            ):
                db.add_all(
                    [
                        WhatsAppContact(
                            user_id=7,
                            encrypted_phone=encrypt_phone_number(
                                "+27123456789",
                            ),
                            phone_lookup_hash=phone_lookup_hash(
                                "+27123456789",
                            ),
                            verified_at=now,
                            opted_in_at=now,
                        ),
                        WhatsAppContact(
                            user_id=8,
                            encrypted_phone=encrypt_phone_number(
                                "+27987654321",
                            ),
                            phone_lookup_hash=phone_lookup_hash(
                                "+27987654321",
                            ),
                            verified_at=now,
                            opted_in_at=now,
                            last_inbound_at=now,
                        ),
                    ],
                )
            db.add(
                Message(
                    message_id=1,
                    conversation_id=28,
                    sender_id=8,
                    content="Original",
                    status="sent",
                    sent_at=now,
                ),
            )
            db.add(
                WhatsAppMessage(
                    whatsapp_message_id=1,
                    provider_message_id="wamid.original",
                    message_id=1,
                    conversation_id=28,
                    sender_user_id=8,
                    recipient_user_id=7,
                    direction="outbound",
                    delivery_status="sent",
                ),
            )
            db.commit()
            provider = Mock()
            provider.send_text.return_value = "wamid.relayed"
            provider.send_template.return_value = "wamid.template"
            service = WhatsAppService(db, provider=provider)
            payload = {
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "id": "wamid.inbound",
                                            "from": "27123456789",
                                            "type": "text",
                                            "text": {"body": "Hello"},
                                            "context": {
                                                "id": "wamid.original",
                                            },
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                ],
            }

            with (
                patch(
                    "app.services.whatsapp_service.get_settings",
                    return_value=make_settings(),
                ),
                patch(
                    "app.core.whatsapp_privacy.get_settings",
                    return_value=make_settings(),
                ),
            ):
                service.receive_webhook(payload)
                service.receive_webhook(payload)
                service.receive_webhook(
                    {
                        "entry": [
                            {
                                "changes": [
                                    {
                                        "value": {
                                            "messages": [
                                                {
                                                    "id": "wamid.phone",
                                                    "from": "27123456789",
                                                    "type": "text",
                                                    "text": {
                                                        "body": (
                                                            "Call "
                                                            "+27123456789"
                                                        ),
                                                    },
                                                    "context": {
                                                        "id": "wamid.original",
                                                    },
                                                },
                                            ],
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                )

            self.assertEqual(
                db.scalar(
                    select(func.count(Message.message_id)).where(
                        Message.conversation_id == 28,
                        Message.content == "Hello",
                    ),
                ),
                1,
            )
            inbound_records = list(
                db.scalars(
                    select(WhatsAppMessage).where(
                        WhatsAppMessage.direction == "inbound",
                    ),
                ).all(),
            )
            outbound_records = list(
                db.scalars(
                    select(WhatsAppMessage).where(
                        WhatsAppMessage.direction == "outbound",
                        WhatsAppMessage.message_id
                        == inbound_records[0].message_id,
                    ),
                ).all(),
            )
            self.assertEqual(len(inbound_records), 1)
            self.assertEqual(len(outbound_records), 1)
            self.assertEqual(
                inbound_records[0].message_id,
                outbound_records[0].message_id,
            )
            self.assertEqual(
                service.delivery_statuses_for_messages(
                    [inbound_records[0].message_id],
                    7,
                ),
                {inbound_records[0].message_id: "sent"},
            )
            self.assertEqual(
                service.delivery_statuses_for_messages(
                    [inbound_records[0].message_id],
                    8,
                ),
                {},
            )
            self.assertEqual(provider.send_text.call_count, 2)
            for call in provider.send_text.call_args_list:
                self.assertNotIn("+27123456789", call.args[1])
        finally:
            event.remove(Message, "before_insert", assign_message_id)
            event.remove(WhatsAppMessage, "before_insert", assign_whatsapp_id)
            db.close()
            engine.dispose()

    def test_phone_link_requires_and_limits_one_time_verification(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine, expire_on_commit=False)
        now = datetime(2026, 11, 5, 9)
        db.add(
            User(
                user_id=14,
                full_name="Test User",
                phone_no="private-registration-phone",
                email="test@example.com",
                created_at=now,
            ),
        )
        db.commit()
        provider = Mock()
        service = WhatsAppService(db, provider=provider)

        try:
            with (
                patch(
                    "app.services.whatsapp_service.get_settings",
                    return_value=make_settings(),
                ),
                patch(
                    "app.core.whatsapp_privacy.get_settings",
                    return_value=make_settings(),
                ),
            ):
                service.start_verification(14, "+27123456789")
                contact = db.get(WhatsAppContact, 14)
                self.assertIsNotNone(contact)
                self.assertNotIn("+27123456789", contact.encrypted_phone)
                self.assertIsNone(contact.verified_at)
                provider.send_template.assert_called_once()
                verification_code = provider.send_template.call_args.args[2]

                with self.assertRaises(WhatsAppVerificationError):
                    service.confirm_verification(14, "000000")
                self.assertEqual(contact.verification_attempts, 1)

                service.confirm_verification(14, verification_code)

            self.assertTrue(service.status_for_user(14))
            self.assertIsNotNone(contact.verified_at)
            self.assertIsNotNone(contact.opted_in_at)
            self.assertIsNone(contact.verification_code_hash)
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
