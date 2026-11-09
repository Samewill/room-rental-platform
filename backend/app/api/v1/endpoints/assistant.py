import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.assistant import AssistantConversation, AssistantMessage
from app.models.user import User
from app.schemas.assistant import (
    AssistantConfirmListingResponse,
    AssistantConversationCreateRequest,
    AssistantConversationDetailResponse,
    AssistantConversationResponse,
    AssistantMessageCreateRequest,
    AssistantMessageResponse,
)
from app.schemas.listing import ListingResponse
from app.services.assistant_graph import AssistantProviderError
from app.services.assistant_service import (
    AssistantConversationNotFoundError,
    AssistantListingAlreadyCreatedError,
    AssistantListingNotReadyError,
    AssistantRolePermissionError,
    AssistantService,
)
from app.services.landlord_listing_service import (
    ListingAmenityNotFoundError,
    ListingAreaNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["AI assistant"])


def get_assistant_service(
    db: Session = Depends(get_db),
) -> AssistantService:
    return AssistantService(db, get_settings())


def _message_response(
    message: AssistantMessage,
) -> AssistantMessageResponse:
    return AssistantMessageResponse(
        message_id=message.message_id,
        sender_role=message.sender_role,
        content=message.content,
        created_at=message.created_at,
        **(message.payload or {}),
    )


@router.get(
    "/conversations",
    response_model=list[AssistantConversationResponse],
)
def list_assistant_conversations(
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> list[AssistantConversationResponse]:
    try:
        conversations = service.list_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve assistant conversations")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant conversations are temporarily unavailable.",
        ) from exc

    return [
        AssistantConversationResponse.model_validate(conversation)
        for conversation in conversations
    ]


@router.post(
    "/conversations",
    response_model=AssistantConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assistant_conversation(
    request: AssistantConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantConversationResponse:
    try:
        conversation = service.create_conversation(
            current_user.user_id,
            request.assistant_role,
        )
    except AssistantRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to create assistant conversation")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant conversation could not be created.",
        ) from exc

    return AssistantConversationResponse.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationDetailResponse,
)
def get_assistant_conversation(
    conversation_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantConversationDetailResponse:
    try:
        conversation, messages = service.get_conversation(
            conversation_id,
            current_user.user_id,
        )
    except AssistantConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AssistantRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to retrieve assistant conversation %s",
            conversation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant conversation is temporarily unavailable.",
        ) from exc

    return AssistantConversationDetailResponse(
        conversation_id=conversation.conversation_id,
        assistant_role=conversation.assistant_role,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_message_response(message) for message in messages],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AssistantMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_assistant_message(
    request: AssistantMessageCreateRequest,
    conversation_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantMessageResponse:
    try:
        _, message = service.send_message(
            conversation_id,
            current_user.user_id,
            request.content,
        )
    except AssistantConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AssistantRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except AssistantProviderError as exc:
        logger.warning(
            "AI assistant request failed for user %s: %s",
            current_user.user_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to send assistant message for conversation %s",
            conversation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant response could not be saved.",
        ) from exc

    return _message_response(message)


@router.post(
    "/conversations/{conversation_id}/confirm-listing",
    response_model=AssistantConfirmListingResponse,
)
def confirm_assistant_listing(
    conversation_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantConfirmListingResponse:
    try:
        _, listing = service.confirm_listing(
            conversation_id,
            current_user.user_id,
        )
    except AssistantConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AssistantRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except AssistantListingNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AssistantListingAlreadyCreatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (ListingAreaNotFoundError, ListingAmenityNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to confirm listing for assistant conversation %s",
            conversation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The listing could not be created right now.",
        ) from exc

    return AssistantConfirmListingResponse(
        conversation_id=conversation_id,
        listing=ListingResponse.model_validate(listing),
    )
