import base64
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import SecretStr, ValidationError

from app.core.whatsapp_privacy import (
    contains_phone_number,
    decrypt_phone_number,
    encrypt_phone_number,
    normalize_phone_number,
    phone_lookup_hash,
    redact_phone_numbers,
)
from app.models.conversation import Message
from app.models.user import User
from app.schemas.conversation import MessageCreateRequest, MessageResponse
from app.schemas.user import UserResponse


def make_settings() -> SimpleNamespace:
    encryption_key = base64.urlsafe_b64encode(b"e" * 32).decode("ascii")
    return SimpleNamespace(
        whatsapp_phone_encryption_key=SecretStr(encryption_key),
        whatsapp_phone_lookup_key=SecretStr("l" * 32),
    )


class WhatsAppPrivacyTests(unittest.TestCase):
    def test_phone_number_is_encrypted_and_keyed_for_lookup(self) -> None:
        settings = make_settings()
        with patch(
            "app.core.whatsapp_privacy.get_settings",
            return_value=settings,
        ):
            encrypted = encrypt_phone_number("+27123456789")
            lookup_hash = phone_lookup_hash("+27123456789")

            self.assertNotIn("+27123456789", encrypted)
            self.assertNotIn("+27123456789", lookup_hash)
            self.assertEqual(decrypt_phone_number(encrypted), "+27123456789")
            self.assertEqual(
                lookup_hash,
                phone_lookup_hash("+27123456789"),
            )

    def test_phone_number_requires_e164_format(self) -> None:
        self.assertEqual(
            normalize_phone_number(" +27123456789 "),
            "+27123456789",
        )
        with self.assertRaises(ValueError):
            normalize_phone_number("07123456789")

    def test_message_inputs_reject_phone_numbers_and_responses_redact_legacy(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            MessageCreateRequest(content="Call me at +27123456789")

        message = Message(
            message_id=1,
            conversation_id=2,
            sender_id=3,
            content="Legacy number +27123456789",
            status="sent",
            sent_at=datetime(2026, 11, 5, 9),
        )
        response = MessageResponse.model_validate(message)
        self.assertEqual(
            response.model_dump()["content"],
            "Legacy number [phone number removed]",
        )

    def test_public_user_profile_never_serializes_phone_number(self) -> None:
        user = User(
            user_id=4,
            full_name="Test User",
            phone_no="+27123456789",
            email="user@example.com",
            created_at=datetime(2026, 11, 5, 9),
        )

        response = UserResponse.model_validate(user).model_dump()

        self.assertNotIn("phone_no", response)

    def test_phone_detection_and_redaction(self) -> None:
        self.assertTrue(contains_phone_number("Call +27 12 345 6789"))
        self.assertFalse(contains_phone_number("The room costs 8500 monthly"))
        self.assertEqual(
            redact_phone_numbers("Call +27123456789"),
            "Call [phone number removed]",
        )


if __name__ == "__main__":
    unittest.main()
