import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.whatsapp_privacy import (
    contains_phone_number,
    decrypt_phone_number,
    encrypt_phone_number,
    normalize_phone_number,
    phone_lookup_hash,
    verification_code_hash,
)
from app.models.conversation import (
    Conversation,
    ConversationParticipant,
    Message,
)
from app.models.whatsapp import WhatsAppContact, WhatsAppMessage
from app.models.saved_search import SavedSearch
from app.services.whatsapp_provider import (
    WhatsAppCloudAPI,
    WhatsAppProviderError,
)


logger = logging.getLogger(__name__)
_ROUTE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_ROUTE_CODE_PATTERN = re.compile(
    r"^\s*ref(?:erence)?\s*[:#]?\s*([A-Z2-9]{8})\s*[:\-]\s*",
    re.IGNORECASE,
)
_CONVERSATION_WINDOW = timedelta(hours=24)
_MAX_VERIFICATION_ATTEMPTS = 5
_VERIFICATION_LIFETIME = timedelta(minutes=10)
_VERIFICATION_RESEND_DELAY = timedelta(seconds=60)


class WhatsAppPermissionError(Exception):
    pass


class WhatsAppVerificationError(Exception):
    pass


class WhatsAppRetryUnavailableError(Exception):
    pass


class WhatsAppService:
    def __init__(
        self,
        db: Session,
        provider: WhatsAppCloudAPI | None = None,
    ) -> None:
        self._db = db
        self._provider = provider or WhatsAppCloudAPI()

    def status_for_user(self, user_id: int) -> bool:
        contact = self._db.get(WhatsAppContact, user_id)
        return self._is_enabled(contact)

    def start_verification(
        self,
        user_id: int,
        phone_number: str,
    ) -> None:
        normalized_phone = normalize_phone_number(phone_number)
        lookup_hash = phone_lookup_hash(normalized_phone)
        now = self._now()
        existing_owner = self._db.scalar(
            select(WhatsAppContact).where(
                WhatsAppContact.phone_lookup_hash == lookup_hash,
                WhatsAppContact.user_id != user_id,
            ),
        )
        if existing_owner is not None:
            raise WhatsAppVerificationError(
                "This WhatsApp number cannot be linked to this account.",
            )

        contact = self._db.get(WhatsAppContact, user_id)
        if (
            contact is not None
            and contact.verification_sent_at is not None
            and now - contact.verification_sent_at
            < _VERIFICATION_RESEND_DELAY
        ):
            raise WhatsAppVerificationError(
                "Please wait before requesting another verification code.",
            )

        code = f"{secrets.randbelow(900_000) + 100_000:06d}"
        if contact is None:
            contact = WhatsAppContact(
                user_id=user_id,
                encrypted_phone=encrypt_phone_number(normalized_phone),
                phone_lookup_hash=lookup_hash,
            )
            self._db.add(contact)
        else:
            contact.encrypted_phone = encrypt_phone_number(normalized_phone)
            contact.phone_lookup_hash = lookup_hash
            contact.verified_at = None
            contact.opted_in_at = None
            contact.opted_out_at = None

        self._db.execute(
            update(SavedSearch)
            .where(SavedSearch.tenant_id == user_id)
            .values(alerts_enabled=False, alerts_opted_in_at=None),
        )
        contact.verification_code_hash = verification_code_hash(user_id, code)
        contact.verification_expires_at = now + _VERIFICATION_LIFETIME
        contact.verification_attempts = 0
        contact.verification_sent_at = now
        self._commit()
        self._provider.send_template(
            normalized_phone,
            get_settings().whatsapp_verification_template_name,
            code,
        )

    def confirm_verification(self, user_id: int, code: str) -> None:
        contact = self._db.get(WhatsAppContact, user_id)
        now = self._now()
        if (
            contact is None
            or contact.verification_code_hash is None
            or contact.verification_expires_at is None
            or contact.verification_expires_at < now
            or contact.verification_attempts >= _MAX_VERIFICATION_ATTEMPTS
        ):
            raise WhatsAppVerificationError(
                "The verification code is invalid or expired.",
            )

        expected_hash = verification_code_hash(user_id, code)
        if not hmac.compare_digest(
            contact.verification_code_hash,
            expected_hash,
        ):
            contact.verification_attempts += 1
            self._commit()
            raise WhatsAppVerificationError(
                "The verification code is invalid or expired.",
            )

        contact.verification_code_hash = None
        contact.verification_expires_at = None
        contact.verification_attempts = 0
        contact.verified_at = now
        contact.opted_in_at = now
        contact.opted_out_at = None
        self._commit()

    def unlink(self, user_id: int) -> None:
        contact = self._db.get(WhatsAppContact, user_id)
        if contact is not None:
            self._db.delete(contact)
        self._db.execute(
            update(SavedSearch)
            .where(SavedSearch.tenant_id == user_id)
            .values(alerts_enabled=False, alerts_opted_in_at=None),
        )
        self._commit()

    def deliver_website_message(
        self,
        message_id: int,
        sender_user_id: int,
    ) -> None:
        message = self._db.get(Message, message_id)
        if message is None or message.sender_id != sender_user_id:
            raise WhatsAppPermissionError("Message is not available.")

        recipient_user_id = self._recipient_for_message(
            message.conversation_id,
            sender_user_id,
        )
        if recipient_user_id is None:
            return
        self._deliver_message(message, sender_user_id, recipient_user_id)

    def retry_delivery(
        self,
        conversation_id: int,
        message_id: int,
        sender_user_id: int,
    ) -> Message:
        message = self._db.get(Message, message_id)
        if (
            message is None
            or message.conversation_id != conversation_id
            or message.sender_id != sender_user_id
        ):
            raise WhatsAppPermissionError("Message is not available.")

        delivery = self._db.scalar(
            select(WhatsAppMessage).where(
                WhatsAppMessage.message_id == message_id,
                WhatsAppMessage.sender_user_id == sender_user_id,
                WhatsAppMessage.direction == "outbound",
            ),
        )
        if delivery is None or delivery.delivery_status != "failed":
            raise WhatsAppRetryUnavailableError(
                "This WhatsApp delivery cannot be retried.",
            )
        if not self._is_enabled(
            self._db.get(WhatsAppContact, delivery.recipient_user_id),
        ):
            raise WhatsAppRetryUnavailableError(
                "WhatsApp delivery is no longer available.",
            )

        self._deliver_message(
            message,
            sender_user_id,
            delivery.recipient_user_id,
        )
        return message

    def delivery_statuses_for_messages(
        self,
        message_ids: list[int],
        user_id: int,
    ) -> dict[int, str]:
        if not message_ids:
            return {}
        rows = self._db.execute(
            select(
                WhatsAppMessage.message_id,
                WhatsAppMessage.delivery_status,
            ).where(
                WhatsAppMessage.message_id.in_(message_ids),
                WhatsAppMessage.sender_user_id == user_id,
                WhatsAppMessage.direction == "outbound",
            ),
        ).all()
        return {
            message_id: delivery_status
            for message_id, delivery_status in rows
        }

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature: str | None,
    ) -> bool:
        app_secret = get_settings().whatsapp_app_secret
        if app_secret is None or signature is None:
            return False
        expected = "sha256=" + hmac.digest(
            app_secret.get_secret_value().encode("utf-8"),
            raw_body,
            "sha256",
        ).hex()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_challenge(self, mode: str, token: str) -> bool:
        verify_token = get_settings().whatsapp_verify_token
        return (
            mode == "subscribe"
            and verify_token is not None
            and hmac.compare_digest(
                verify_token.get_secret_value(),
                token,
            )
        )

    def receive_webhook(self, payload: dict[str, object]) -> None:
        for event in self._incoming_events(payload):
            try:
                self._receive_event(event)
            except WhatsAppProviderError:
                logger.exception("WhatsApp relay delivery failed")

    def _receive_event(self, event: dict[str, object]) -> None:
        provider_message_id = event.get("id")
        sender = event.get("from")
        message_type = event.get("type")
        if (
            not isinstance(provider_message_id, str)
            or not provider_message_id
            or not isinstance(sender, str)
            or not sender.isascii()
            or not sender.isdigit()
            or message_type != "text"
        ):
            return
        text = event.get("text")
        content = text.get("body") if isinstance(text, dict) else None
        if not isinstance(content, str):
            return

        try:
            sender_phone = normalize_phone_number(f"+{sender}")
        except ValueError:
            return
        contact = self._db.scalar(
            select(WhatsAppContact).where(
                WhatsAppContact.phone_lookup_hash
                == phone_lookup_hash(sender_phone),
            ),
        )
        if not self._is_enabled(contact):
            return
        if content.strip().casefold() == "stop":
            self.unlink(contact.user_id)
            self._provider.send_text(
                sender_phone,
                "WhatsApp messages for your account have been turned off.",
            )
            return
        if contains_phone_number(content):
            self._provider.send_text(
                sender_phone,
                "Phone numbers cannot be shared in platform messages.",
            )
            return
        if not content.strip() or len(content.strip()) > 4000:
            return

        conversation, message_content = self._resolve_conversation(
            contact.user_id,
            event,
            content.strip(),
            sender_phone,
        )
        if conversation is None:
            return
        if not message_content:
            self._provider.send_text(
                sender_phone,
                "Include a message after the conversation reference.",
            )
            return

        recipient_user_id = self._recipient_for_message(
            conversation.conversation_id,
            contact.user_id,
        )
        if recipient_user_id is None:
            return
        message = Message(
            conversation_id=conversation.conversation_id,
            sender_id=contact.user_id,
            content=message_content,
            status="sent",
        )
        mapping = WhatsAppMessage(
            provider_message_id=provider_message_id,
            conversation_id=conversation.conversation_id,
            sender_user_id=contact.user_id,
            recipient_user_id=recipient_user_id,
            direction="inbound",
            delivery_status="received",
        )
        now = self._now()
        contact.last_inbound_at = now
        try:
            with self._db.begin_nested():
                self._db.add(message)
                self._db.flush()
                mapping.message_id = message.message_id
                self._db.add(mapping)
                self._db.flush()
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            duplicate = self._db.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.provider_message_id
                    == provider_message_id,
                ),
            )
            if duplicate is not None:
                return
            raise

        self._deliver_message(
            message,
            contact.user_id,
            recipient_user_id,
            conversation=conversation,
        )

    def _resolve_conversation(
        self,
        user_id: int,
        event: dict[str, object],
        content: str,
        sender_phone: str,
    ) -> tuple[Conversation | None, str]:
        context = event.get("context")
        if isinstance(context, dict):
            context_id = context.get("id")
            if not isinstance(context_id, str):
                return None, content
            original = self._db.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.provider_message_id == context_id,
                    WhatsAppMessage.direction == "outbound",
                    WhatsAppMessage.recipient_user_id == user_id,
                ),
            )
            if original is not None:
                conversation = self._participant_conversation(
                    original.conversation_id,
                    user_id,
                )
                if conversation is not None:
                    return conversation, content
            self._provider.send_text(
                sender_phone,
                "That reply could not be matched. Reply to a platform "
                "message or include its conversation reference.",
            )
            return None, content

        match = _ROUTE_CODE_PATTERN.match(content)
        if match is not None:
            route_code = match.group(1).upper()
            conversation = self._db.scalar(
                select(Conversation)
                .join(
                    ConversationParticipant,
                    ConversationParticipant.conversation_id
                    == Conversation.conversation_id,
                )
                .where(
                    Conversation.whatsapp_route_code == route_code,
                    ConversationParticipant.user_id == user_id,
                ),
            )
            if conversation is not None:
                return conversation, content[match.end():].strip()
            self._provider.send_text(
                sender_phone,
                "That conversation reference is not available. Use a "
                "reference from a platform message.",
            )
            return None, content

        conversations = self._participant_conversations(user_id)
        if len(conversations) == 1:
            return conversations[0], content
        if len(conversations) > 1:
            codes = [
                self._ensure_route_code(conversation)
                for conversation in conversations
            ]
            self._commit()
            self._provider.send_text(
                sender_phone,
                "Reply to a platform message, or start your reply with "
                f"Ref CODE: (choose one: {', '.join(codes)}).",
            )
        return None, content

    def _deliver_message(
        self,
        message: Message,
        sender_user_id: int,
        recipient_user_id: int,
        conversation: Conversation | None = None,
    ) -> None:
        contact = self._db.get(WhatsAppContact, recipient_user_id)
        if not self._is_enabled(contact):
            return
        if contains_phone_number(message.content):
            raise WhatsAppVerificationError(
                "Phone numbers cannot be shared in platform messages.",
            )
        if conversation is None:
            conversation = self._participant_conversation(
                message.conversation_id,
                sender_user_id,
            )
        if conversation is None:
            return

        existing = self._db.scalar(
            select(WhatsAppMessage).where(
                WhatsAppMessage.message_id == message.message_id,
                WhatsAppMessage.direction == "outbound",
            ),
        )
        if existing is not None and existing.delivery_status == "sent":
            return
        if existing is None:
            existing = WhatsAppMessage(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                sender_user_id=sender_user_id,
                recipient_user_id=recipient_user_id,
                direction="outbound",
                delivery_status="failed",
            )
            self._db.add(existing)
            self._db.flush()

        route_code = self._ensure_route_code(conversation)
        self._commit()
        phone_number = decrypt_phone_number(contact.encrypted_phone)
        outbound_content = (
            f"Ref {route_code}: {message.content}\nReply STOP to opt out."
        )
        now = self._now()
        is_in_session = (
            contact.last_inbound_at is not None
            and now - contact.last_inbound_at < _CONVERSATION_WINDOW
        )
        if is_in_session:
            provider_id = self._provider.send_text(
                phone_number,
                outbound_content,
            )
        else:
            provider_id = self._provider.send_template(
                phone_number,
                get_settings().whatsapp_message_template_name,
                outbound_content,
            )

        existing.provider_message_id = provider_id
        existing.delivery_status = "sent"
        existing.delivered_at = now
        self._commit()

    def _participant_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        return self._db.scalar(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.conversation_id,
            )
            .where(
                Conversation.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            ),
        )

    def _participant_conversations(self, user_id: int) -> list[Conversation]:
        statement = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.conversation_id,
            )
            .where(ConversationParticipant.user_id == user_id)
            .order_by(Conversation.conversation_id)
        )
        return list(self._db.scalars(statement).all())

    def _recipient_for_message(
        self,
        conversation_id: int,
        sender_user_id: int,
    ) -> int | None:
        participant_ids = list(
            self._db.scalars(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id
                    == conversation_id,
                ),
            ).all(),
        )
        if sender_user_id not in participant_ids:
            return None
        recipients = [
            participant_id
            for participant_id in participant_ids
            if participant_id != sender_user_id
        ]
        return recipients[0] if len(recipients) == 1 else None

    def _ensure_route_code(self, conversation: Conversation) -> str:
        if conversation.whatsapp_route_code is None:
            conversation.whatsapp_route_code = "".join(
                secrets.choice(_ROUTE_CODE_ALPHABET)
                for _ in range(8)
            )
            self._db.flush()
        return conversation.whatsapp_route_code

    @staticmethod
    def _is_enabled(contact: WhatsAppContact | None) -> bool:
        return (
            contact is not None
            and contact.verified_at is not None
            and contact.opted_in_at is not None
            and contact.opted_out_at is None
        )

    @staticmethod
    def _incoming_events(
        payload: dict[str, object],
    ) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        entries = payload.get("entry")
        if not isinstance(entries, list):
            return events
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            changes = entry.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                messages = value.get("messages")
                if isinstance(messages, list):
                    events.extend(
                        item for item in messages if isinstance(item, dict)
                    )
        return events

    def _commit(self) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
