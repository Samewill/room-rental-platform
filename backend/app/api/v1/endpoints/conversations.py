import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.whatsapp import get_whatsapp_service
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import (
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.conversation_service import (
    ConversationMessagePermissionError,
    ConversationNotFoundError,
    ConversationService,
)
from app.services.whatsapp_provider import WhatsAppProviderError
from app.services.whatsapp_service import WhatsAppService
from app.services.whatsapp_service import (
    WhatsAppPermissionError,
    WhatsAppRetryUnavailableError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversations"])


def get_conversation_service(
    db: Session = Depends(get_db),
) -> ConversationService:
    return ConversationService(db)


@router.get(
    "/users/me/conversations",
    response_model=list[ConversationResponse],
)
def list_my_conversations(
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    try:
        conversations = service.list_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve user conversations")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversations are temporarily unavailable.",
        ) from exc

    return [
        ConversationResponse.model_validate(conversation)
        for conversation in conversations
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def list_conversation_messages(
    conversation_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    whatsapp: WhatsAppService = Depends(get_whatsapp_service),
) -> list[MessageResponse]:
    try:
        messages = service.list_messages(
            conversation_id,
            current_user.user_id,
        )
        delivery_statuses = whatsapp.delivery_statuses_for_messages(
            [message.message_id for message in messages],
            current_user.user_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to retrieve messages for conversation %s",
            conversation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Messages are temporarily unavailable.",
        ) from exc

    return [
        MessageResponse.model_validate(message).model_copy(
            update={
                "whatsapp_delivery_status": delivery_statuses.get(
                    message.message_id,
                ),
            },
        )
        for message in messages
    ]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_conversation_message(
    request: MessageCreateRequest,
    conversation_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    whatsapp: WhatsAppService = Depends(get_whatsapp_service),
) -> MessageResponse:
    try:
        message = service.send_message(
            conversation_id,
            current_user.user_id,
            request.content,
        )
        try:
            whatsapp.deliver_website_message(
                message.message_id,
                current_user.user_id,
            )
        except (RuntimeError, WhatsAppProviderError):
            logger.exception(
                "Message %s was saved but WhatsApp delivery failed",
                message.message_id,
            )
            delivery_status = "failed"
        else:
            delivery_status = whatsapp.delivery_statuses_for_messages(
                [message.message_id],
                current_user.user_id,
            ).get(message.message_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to send message to conversation %s",
            conversation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message could not be sent right now.",
        ) from exc
    response = MessageResponse.model_validate(message)
    return response.model_copy(
        update={"whatsapp_delivery_status": delivery_status},
    )


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/whatsapp/retry",
    response_model=MessageResponse,
)
def retry_whatsapp_delivery(
    conversation_id: Annotated[int, Path(gt=0)],
    message_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    whatsapp: WhatsAppService = Depends(get_whatsapp_service),
) -> MessageResponse:
    try:
        messages = service.list_messages(
            conversation_id,
            current_user.user_id,
        )
        message = next(
            (
                message
                for message in messages
                if message.message_id == message_id
            ),
            None,
        )
        if message is None:
            raise ConversationNotFoundError("Message not found.")
        try:
            whatsapp.retry_delivery(
                conversation_id,
                message_id,
                current_user.user_id,
            )
        except (RuntimeError, WhatsAppProviderError):
            logger.exception(
                "WhatsApp delivery retry failed for message %s",
                message_id,
            )
            delivery_status = "failed"
        else:
            delivery_status = whatsapp.delivery_statuses_for_messages(
                [message_id],
                current_user.user_id,
            ).get(message_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation or message not found.",
        ) from exc
    except WhatsAppPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except WhatsAppRetryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "WhatsApp delivery retry could not be completed for message %s",
            message_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp delivery could not be retried right now.",
        ) from exc

    return MessageResponse.model_validate(message).model_copy(
        update={"whatsapp_delivery_status": delivery_status},
    )


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/read",
    response_model=MessageResponse,
)
def mark_conversation_message_read(
    conversation_id: Annotated[int, Path(gt=0)],
    message_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> MessageResponse:
    try:
        message = service.mark_message_read(
            conversation_id,
            message_id,
            current_user.user_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationMessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to update read status for message %s",
            message_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message status could not be updated right now.",
        ) from exc

    return MessageResponse.model_validate(message)
