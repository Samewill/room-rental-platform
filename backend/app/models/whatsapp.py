from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WhatsAppContact(Base):
    __tablename__ = "whatsapp_contacts"
    __table_args__ = (
        UniqueConstraint(
            "phone_lookup_hash",
            name="whatsapp_contacts_phone_lookup_hash_key",
        ),
        CheckConstraint(
            "verification_attempts BETWEEN 0 AND 5",
            name="whatsapp_contacts_verification_attempts_check",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="whatsapp_contacts_user_id_fkey",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    encrypted_phone: Mapped[str] = mapped_column(String(128), nullable=False)
    phone_lookup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_code_hash: Mapped[str | None] = mapped_column(String(64))
    verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    verification_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    opted_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    opted_out_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        UniqueConstraint(
            "provider_message_id",
            name="whatsapp_messages_provider_message_id_key",
        ),
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="whatsapp_messages_direction_check",
        ),
        CheckConstraint(
            "delivery_status IN ('received', 'sent', 'failed')",
            name="whatsapp_messages_delivery_status_check",
        ),
    )

    whatsapp_message_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "messages.message_id",
            name="whatsapp_messages_message_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "conversations.conversation_id",
            name="whatsapp_messages_conversation_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sender_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="whatsapp_messages_sender_user_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    recipient_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            name="whatsapp_messages_recipient_user_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
