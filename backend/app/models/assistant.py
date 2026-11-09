from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    JSON,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (
        CheckConstraint(
            "assistant_role IN ('tenant', 'landlord')",
            name="assistant_conversations_role_check",
        ),
        Index(
            "assistant_conversations_owner_updated_idx",
            "owner_user_id",
            "updated_at",
        ),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    owner_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    assistant_role: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_state: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    messages: Mapped[list[AssistantMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="(AssistantMessage.created_at, AssistantMessage.message_id)",
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (
        CheckConstraint(
            "sender_role IN ('user', 'assistant')",
            name="assistant_messages_sender_role_check",
        ),
        CheckConstraint(
            "length(trim(content)) BETWEEN 1 AND 4000",
            name="assistant_messages_content_length_check",
        ),
        Index(
            "assistant_messages_conversation_created_idx",
            "conversation_id",
            "created_at",
            "message_id",
        ),
    )

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "assistant_conversations.conversation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sender_role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    conversation: Mapped[AssistantConversation] = relationship(
        back_populates="messages",
    )
