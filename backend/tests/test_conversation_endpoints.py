import unittest
from datetime import datetime
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.conversations import get_conversation_service
from app.api.v1.endpoints.whatsapp import get_whatsapp_service
from app.api.v1.router import api_router
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.services.conversation_service import (
    ConversationMessagePermissionError,
    ConversationNotFoundError,
)
from app.services.whatsapp_provider import WhatsAppProviderError


class ConversationEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.whatsapp = Mock()
        self.whatsapp.delivery_statuses_for_messages.return_value = {}
        self.user = User(user_id=8)
        self.app.dependency_overrides[get_conversation_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[get_whatsapp_service] = (
            lambda: self.whatsapp
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_conversation() -> Conversation:
        return Conversation(
            conversation_id=4,
            contact_request_id=12,
            created_at=datetime(2026, 11, 2, 9),
        )

    @staticmethod
    def make_message() -> Message:
        return Message(
            message_id=7,
            conversation_id=4,
            sender_id=8,
            content="Hello",
            status="sent",
            sent_at=datetime(2026, 11, 2, 9),
        )

    def test_list_conversations_uses_current_user(self) -> None:
        self.service.list_for_user.return_value = [self.make_conversation()]

        response = self.client.get("/api/v1/users/me/conversations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["contact_request_id"], 12)
        self.service.list_for_user.assert_called_once_with(8)

    def test_list_messages_uses_current_user(self) -> None:
        self.service.list_messages.return_value = [self.make_message()]
        self.whatsapp.delivery_statuses_for_messages.return_value = {
            7: "sent",
        }

        response = self.client.get(
            "/api/v1/conversations/4/messages",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["content"], "Hello")
        self.assertEqual(
            response.json()[0]["whatsapp_delivery_status"],
            "sent",
        )
        self.service.list_messages.assert_called_once_with(4, 8)
        self.whatsapp.delivery_statuses_for_messages.assert_called_once_with(
            [7],
            8,
        )

    def test_nonparticipant_conversation_is_not_found(self) -> None:
        self.service.list_messages.side_effect = ConversationNotFoundError(
            "Conversation not found.",
        )

        response = self.client.get("/api/v1/conversations/4/messages")

        self.assertEqual(response.status_code, 404)

    def test_send_message_uses_current_user(self) -> None:
        self.service.send_message.return_value = self.make_message()

        response = self.client.post(
            "/api/v1/conversations/4/messages",
            json={"content": "Hello"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["whatsapp_delivery_status"])
        self.service.send_message.assert_called_once_with(4, 8, "Hello")

    def test_send_message_returns_explicit_whatsapp_failure_status(self) -> None:
        self.service.send_message.return_value = self.make_message()
        self.whatsapp.deliver_website_message.side_effect = (
            WhatsAppProviderError("delivery failed")
        )

        response = self.client.post(
            "/api/v1/conversations/4/messages",
            json={"content": "Hello"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["whatsapp_delivery_status"],
            "failed",
        )

    def test_whatsapp_retry_returns_delivery_status(self) -> None:
        self.service.list_messages.return_value = [self.make_message()]
        self.whatsapp.delivery_statuses_for_messages.return_value = {
            7: "sent",
        }

        response = self.client.post(
            "/api/v1/conversations/4/messages/7/whatsapp/retry",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["whatsapp_delivery_status"],
            "sent",
        )
        self.whatsapp.retry_delivery.assert_called_once_with(4, 7, 8)

    def test_send_message_validates_content(self) -> None:
        response = self.client.post(
            "/api/v1/conversations/4/messages",
            json={"content": " "},
        )

        self.assertEqual(response.status_code, 422)
        self.service.send_message.assert_not_called()

    def test_send_message_rejects_phone_numbers(self) -> None:
        response = self.client.post(
            "/api/v1/conversations/4/messages",
            json={"content": "Call +27123456789"},
        )

        self.assertEqual(response.status_code, 422)
        self.service.send_message.assert_not_called()

    def test_read_status_endpoint_updates_message(self) -> None:
        self.service.mark_message_read.return_value = self.make_message()

        response = self.client.post(
            "/api/v1/conversations/4/messages/7/read",
        )

        self.assertEqual(response.status_code, 200)
        self.service.mark_message_read.assert_called_once_with(4, 7, 8)

    def test_sender_cannot_mark_own_message_read(self) -> None:
        self.service.mark_message_read.side_effect = (
            ConversationMessagePermissionError("Not permitted.")
        )

        response = self.client.post(
            "/api/v1/conversations/4/messages/7/read",
        )

        self.assertEqual(response.status_code, 403)

    def test_database_errors_are_reported(self) -> None:
        self.service.list_for_user.side_effect = SQLAlchemyError("failed")

        response = self.client.get("/api/v1/users/me/conversations")

        self.assertEqual(response.status_code, 503)

    def test_endpoints_require_authentication(self) -> None:
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.get("/api/v1/users/me/conversations")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
