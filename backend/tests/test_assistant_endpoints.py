import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.assistant import get_assistant_service
from app.api.v1.router import api_router
from app.models.assistant import AssistantConversation, AssistantMessage
from app.models.user import User
from app.schemas.listing import ListingResponse
from app.services.assistant_graph import AssistantProviderError
from app.services.assistant_service import (
    AssistantConversationNotFoundError,
    AssistantRolePermissionError,
)


class AssistantEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.user = User(user_id=8)
        self.app.dependency_overrides[get_assistant_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_conversation() -> AssistantConversation:
        return AssistantConversation(
            conversation_id=4,
            owner_user_id=8,
            assistant_role="tenant",
            workflow_state={},
            created_at=datetime(2026, 11, 5, 9),
            updated_at=datetime(2026, 11, 5, 9),
        )

    @staticmethod
    def make_message() -> AssistantMessage:
        return AssistantMessage(
            message_id=7,
            conversation_id=4,
            sender_role="assistant",
            content="I found one verified room.",
            payload={"listings": [], "draft": None, "created_listing": None},
            created_at=datetime(2026, 11, 5, 9),
        )

    def test_list_conversations_is_scoped_to_current_user(self) -> None:
        self.service.list_for_user.return_value = [self.make_conversation()]

        response = self.client.get("/api/v1/assistant/conversations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["conversation_id"], 4)
        self.service.list_for_user.assert_called_once_with(8)

    def test_create_conversation_uses_requested_role(self) -> None:
        self.service.create_conversation.return_value = self.make_conversation()

        response = self.client.post(
            "/api/v1/assistant/conversations",
            json={"assistant_role": "tenant"},
        )

        self.assertEqual(response.status_code, 201)
        self.service.create_conversation.assert_called_once_with(8, "tenant")

    def test_create_conversation_rejects_role_not_owned_by_user(self) -> None:
        self.service.create_conversation.side_effect = (
            AssistantRolePermissionError("Not permitted.")
        )

        response = self.client.post(
            "/api/v1/assistant/conversations",
            json={"assistant_role": "landlord"},
        )

        self.assertEqual(response.status_code, 403)

    def test_send_message_returns_structured_assistant_response(self) -> None:
        self.service.send_message.return_value = (
            self.make_conversation(),
            self.make_message(),
        )

        response = self.client.post(
            "/api/v1/assistant/conversations/4/messages",
            json={"content": "Find a room"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["content"],
            "I found one verified room.",
        )
        self.service.send_message.assert_called_once_with(4, 8, "Find a room")

    def test_rejection_notification_includes_admin_reason(self) -> None:
        message = self.make_message()
        message.content = (
            'Your listing "Private room" was not approved. Reason: '
            "The availability date is missing."
        )
        message.payload = {
            "listings": [],
            "draft": None,
            "created_listing": None,
            "notification": {
                "kind": "listing_rejected",
                "listing_id": 12,
                "listing_title": "Private room",
                "reason": "The availability date is missing.",
            },
        }
        self.service.get_conversation.return_value = (
            self.make_conversation(),
            [message],
        )

        response = self.client.get("/api/v1/assistant/conversations/4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["messages"][0]["notification"],
            {
                "kind": "listing_rejected",
                "listing_id": 12,
                "listing_title": "Private room",
                "reason": "The availability date is missing.",
            },
        )

    def test_provider_failure_is_reported_as_service_unavailable(self) -> None:
        self.service.send_message.side_effect = AssistantProviderError(
            "No model available.",
        )

        response = self.client.post(
            "/api/v1/assistant/conversations/4/messages",
            json={"content": "Find a room"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "No model available.")

    def test_other_users_cannot_read_assistant_conversations(self) -> None:
        self.service.get_conversation.side_effect = (
            AssistantConversationNotFoundError("Conversation not found.")
        )

        response = self.client.get("/api/v1/assistant/conversations/4")

        self.assertEqual(response.status_code, 404)

    def test_confirm_listing_uses_existing_listing_response(self) -> None:
        listing = ListingResponse(
            listing_id=12,
            area_id=3,
            title="Private room",
            description="A private room.",
            room_type="single_room",
            monthly_rent=Decimal("3000.00"),
            deposit_amount=Decimal("1000.00"),
            address="12 Example Road",
            date_available="2026-12-01",
            status="draft",
            created_at=datetime(2026, 11, 5, 9),
            amenities=[],
            photos=[],
        )
        self.service.confirm_listing.return_value = (
            self.make_conversation(),
            listing,
        )

        response = self.client.post(
            "/api/v1/assistant/conversations/4/confirm-listing",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["listing"]["listing_id"], 12)
        self.service.confirm_listing.assert_called_once_with(4, 8)


if __name__ == "__main__":
    unittest.main()
