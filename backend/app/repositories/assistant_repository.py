from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assistant import AssistantConversation, AssistantMessage


class AssistantRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user(self, user_id: int) -> list[AssistantConversation]:
        statement = (
            select(AssistantConversation)
            .where(AssistantConversation.owner_user_id == user_id)
            .order_by(
                AssistantConversation.updated_at.desc(),
                AssistantConversation.conversation_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def get_for_user(
        self,
        conversation_id: int,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> AssistantConversation | None:
        statement = select(AssistantConversation).where(
            AssistantConversation.conversation_id == conversation_id,
            AssistantConversation.owner_user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def list_messages(
        self,
        conversation_id: int,
    ) -> list[AssistantMessage]:
        statement = (
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(
                AssistantMessage.created_at,
                AssistantMessage.message_id,
            )
        )
        return list(self._db.scalars(statement).all())

    def add_conversation(
        self,
        conversation: AssistantConversation,
    ) -> AssistantConversation:
        self._db.add(conversation)
        self._db.flush()
        return conversation

    def add_listing_moderation_notification(
        self,
        owner_user_id: int,
        listing_id: int,
        listing_title: str,
        decision: str,
        reason: str | None,
    ) -> AssistantConversation:
        approved = decision == "approved"
        notification = {
            "kind": (
                "listing_approved" if approved else "listing_rejected"
            ),
            "listing_id": listing_id,
            "listing_title": listing_title,
            "reason": reason,
        }
        content = (
            (
                f'Good news! Your listing "{listing_title}" has been '
                "approved by the admin team and is now live on Room Rentals."
            )
            if approved
            else (
                f'Your listing "{listing_title}" was not approved and has '
                "been returned to drafts. Reason from the admin team: "
                f"{reason or 'No reason was provided.'} Update your listing "
                "from your landlord dashboard and resubmit it for review."
            )
        )
        conversation = self.add_conversation(
            AssistantConversation(
                owner_user_id=owner_user_id,
                assistant_role="landlord",
                workflow_state={},
            ),
        )
        self.add_message(
            AssistantMessage(
                conversation_id=conversation.conversation_id,
                sender_role="assistant",
                content=content,
                payload={
                    "listings": [],
                    "draft": None,
                    "created_listing": None,
                    "notification": notification,
                },
            ),
        )
        return conversation

    def add_message(
        self,
        message: AssistantMessage,
    ) -> AssistantMessage:
        self._db.add(message)
        self._db.flush()
        return message
