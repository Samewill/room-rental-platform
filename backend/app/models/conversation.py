from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "contact_request_id",
            name="conversations_contact_request_id_key",
        ),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    contact_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "contact_requests.request_id",
            name="conversations_contact_request_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    participants: Mapped[list[ConversationParticipant]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationParticipant.user_id",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="(Message.sent_at, Message.message_id)",
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        Index(
            "conversation_participants_user_id_idx",
            "user_id",
        ),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "conversations.conversation_id",
            name="conversation_participants_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="conversation_participants_user_id_fkey",
        ),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    conversation: Mapped[Conversation] = relationship(
        back_populates="participants",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "length(trim(content)) BETWEEN 1 AND 4000",
            name="messages_content_length_check",
        ),
        CheckConstraint(
            "status IN ('sent', 'read')",
            name="messages_status_check",
        ),
        CheckConstraint(
            "(status = 'sent' AND read_at IS NULL) OR "
            "(status = 'read' AND read_at IS NOT NULL)",
            name="messages_read_status_check",
        ),
        ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="messages_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "sender_id"],
            [
                "conversation_participants.conversation_id",
                "conversation_participants.user_id",
            ],
            name="messages_sender_participant_fkey",
            ondelete="CASCADE",
        ),
        Index(
            "messages_conversation_sent_at_idx",
            "conversation_id",
            "sent_at",
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
        nullable=False,
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="sent",
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    conversation: Mapped[Conversation] = relationship(
        back_populates="messages",
    )
