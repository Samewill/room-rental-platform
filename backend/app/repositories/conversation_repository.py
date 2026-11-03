from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import (
    Conversation,
    ConversationParticipant,
    Message,
)


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_for_contact_request(
        self,
        contact_request_id: int,
        tenant_id: int,
        landlord_id: int,
    ) -> Conversation:
        conversation = Conversation(contact_request_id=contact_request_id)
        self._db.add(conversation)
        self._db.flush()
        conversation.participants.extend(
            [
                ConversationParticipant(user_id=tenant_id),
                ConversationParticipant(user_id=landlord_id),
            ]
        )
        self._db.flush()
        return conversation

    def list_for_participant(self, user_id: int) -> list[Conversation]:
        statement = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.conversation_id,
            )
            .where(ConversationParticipant.user_id == user_id)
            .order_by(
                Conversation.created_at.desc(),
                Conversation.conversation_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def get_for_participant(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        statement = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.conversation_id,
            )
            .where(
                Conversation.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        return self._db.scalar(statement)

    def list_messages(self, conversation_id: int) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at, Message.message_id)
        )
        return list(self._db.scalars(statement).all())

    def get_message(
        self,
        conversation_id: int,
        message_id: int,
    ) -> Message | None:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.message_id == message_id,
        )
        return self._db.scalar(statement)

    def add_message(self, message: Message) -> Message:
        self._db.add(message)
        self._db.flush()
        return message
