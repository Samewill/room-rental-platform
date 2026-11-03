import unittest
from datetime import datetime
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from app.models.conversation import Conversation, Message
from app.services.conversation_service import (
    ConversationMessagePermissionError,
    ConversationNotFoundError,
    ConversationService,
)


class ConversationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = ConversationService(self.db)
        self.repository = Mock()
        self.service._conversations = self.repository

    def test_lists_conversations_only_through_user_scoped_repository(self) -> None:
        conversations = [Mock(spec=Conversation)]
        self.repository.list_for_participant.return_value = conversations

        result = self.service.list_for_user(8)

        self.assertIs(result, conversations)
        self.repository.list_for_participant.assert_called_once_with(8)

    def test_lists_messages_after_authorizing_participant(self) -> None:
        conversation = Mock(spec=Conversation)
        messages = [Mock(spec=Message)]
        self.repository.get_for_participant.return_value = conversation
        self.repository.list_messages.return_value = messages

        result = self.service.list_messages(4, 8)

        self.assertIs(result, messages)
        self.repository.get_for_participant.assert_called_once_with(4, 8)
        self.repository.list_messages.assert_called_once_with(4)

    def test_nonparticipant_cannot_list_messages(self) -> None:
        self.repository.get_for_participant.return_value = None

        with self.assertRaises(ConversationNotFoundError):
            self.service.list_messages(4, 9)

        self.repository.list_messages.assert_not_called()

    def test_sends_trimmed_message_for_participant(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        self.repository.add_message.side_effect = lambda message: message

        result = self.service.send_message(4, 8, "  Hello there  ")

        self.assertEqual(result.content, "Hello there")
        self.assertEqual(result.sender_id, 8)
        self.assertEqual(result.status, "sent")
        self.db.commit.assert_called_once()

    def test_message_rejects_empty_or_oversized_content(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )

        with self.assertRaises(ValueError):
            self.service.send_message(4, 8, "  ")
        with self.assertRaises(ValueError):
            self.service.send_message(4, 8, "x" * 4001)

        self.repository.add_message.assert_not_called()

    def test_send_failure_rolls_back(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        self.repository.add_message.side_effect = SQLAlchemyError("failed")

        with self.assertRaises(SQLAlchemyError):
            self.service.send_message(4, 8, "Hello")

        self.db.rollback.assert_called_once()

    def test_recipient_can_mark_message_read(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        message = Message(
            message_id=5,
            conversation_id=4,
            sender_id=8,
            content="Hello",
            status="sent",
        )
        self.repository.get_message.return_value = message

        result = self.service.mark_message_read(4, 9, 5)

        self.assertEqual(result.status, "read")
        self.assertIsInstance(result.read_at, datetime)
        self.db.commit.assert_called_once()

    def test_sender_cannot_mark_own_message_read(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        self.repository.get_message.return_value = Message(
            message_id=5,
            conversation_id=4,
            sender_id=8,
            content="Hello",
            status="sent",
        )

        with self.assertRaises(ConversationMessagePermissionError):
            self.service.mark_message_read(4, 5, 8)

        self.db.commit.assert_not_called()

    def test_missing_message_is_not_found(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        self.repository.get_message.return_value = None

        with self.assertRaises(ConversationNotFoundError):
            self.service.mark_message_read(4, 9, 5)

    def test_repeated_read_is_idempotent(self) -> None:
        self.repository.get_for_participant.return_value = Mock(
            spec=Conversation,
        )
        message = Message(
            message_id=5,
            conversation_id=4,
            sender_id=8,
            content="Hello",
            status="read",
            read_at=datetime(2026, 11, 2, 10),
        )
        self.repository.get_message.return_value = message

        result = self.service.mark_message_read(4, 9, 5)

        self.assertIs(result, message)
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
