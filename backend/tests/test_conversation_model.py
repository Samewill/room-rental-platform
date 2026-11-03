import unittest

from app.models.conversation import (
    Conversation,
    ConversationParticipant,
    Message,
)


class ConversationModelTests(unittest.TestCase):
    def test_conversation_is_unique_per_contact_request(self) -> None:
        constraints = {
            constraint.name
            for constraint in Conversation.__table__.constraints
        }

        self.assertIn("conversations_contact_request_id_key", constraints)

    def test_message_sender_is_constrained_to_conversation_participant(self) -> None:
        constraints = {
            constraint.name
            for constraint in Message.__table__.constraints
        }

        self.assertIn("messages_sender_participant_fkey", constraints)

    def test_message_status_and_content_constraints_are_registered(self) -> None:
        constraints = {
            constraint.name
            for constraint in Message.__table__.constraints
        }

        self.assertIn("messages_content_length_check", constraints)
        self.assertIn("messages_status_check", constraints)
        self.assertIn("messages_read_status_check", constraints)

    def test_participant_key_is_conversation_and_user(self) -> None:
        primary_key_columns = {
            column.name
            for column in ConversationParticipant.__table__.primary_key.columns
        }

        self.assertEqual(primary_key_columns, {"conversation_id", "user_id"})


if __name__ == "__main__":
    unittest.main()
