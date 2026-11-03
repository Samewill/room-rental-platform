from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository


class ConversationNotFoundError(Exception):
    pass


class ConversationMessagePermissionError(Exception):
    pass


class ConversationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._conversations = ConversationRepository(db)

    def list_for_user(self, user_id: int) -> list[Conversation]:
        return self._conversations.list_for_participant(user_id)

    def list_messages(
        self,
        conversation_id: int,
        user_id: int,
    ) -> list[Message]:
        self._require_participant(conversation_id, user_id)
        return self._conversations.list_messages(conversation_id)

    def send_message(
        self,
        conversation_id: int,
        sender_id: int,
        content: str,
    ) -> Message:
        self._require_participant(conversation_id, sender_id)
        normalized_content = content.strip()
        if not normalized_content or len(normalized_content) > 4000:
            raise ValueError("Message content must be between 1 and 4000 characters.")

        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=normalized_content,
            status="sent",
        )
        try:
            self._conversations.add_message(message)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return message

    def mark_message_read(
        self,
        conversation_id: int,
        message_id: int,
        user_id: int,
    ) -> Message:
        self._require_participant(conversation_id, user_id)
        message = self._conversations.get_message(conversation_id, message_id)
        if message is None:
            raise ConversationNotFoundError("Message not found.")
        if message.sender_id == user_id:
            raise ConversationMessagePermissionError(
                "You cannot mark your own message as read.",
            )

        if message.status == "read":
            return message

        message.status = "read"
        message.read_at = datetime.now()
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return message

    def _require_participant(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation:
        conversation = self._conversations.get_for_participant(
            conversation_id,
            user_id,
        )
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found.")
        return conversation
