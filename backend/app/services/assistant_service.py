from datetime import datetime
from typing import Any, Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.assistant import AssistantConversation, AssistantMessage
from app.repositories.amenity_repository import AmenityRepository
from app.repositories.area_repository import AreaRepository
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.listing_repository import ListingRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.assistant import AssistantRole
from app.schemas.landlord_listing import ListingCreateRequest
from app.schemas.listing import ListingResponse
from app.services.assistant_graph import (
    AssistantProviderError,
    build_assistant_graph,
)
from app.services.amenity_service import AmenityService
from app.services.area_service import AreaService
from app.services.landlord_listing_service import (
    LandlordListingService,
    ListingAmenityNotFoundError,
    ListingAreaNotFoundError,
)
from app.services.listing_service import ListingService


class AssistantConversationNotFoundError(Exception):
    pass


class AssistantRolePermissionError(Exception):
    pass


class AssistantListingNotReadyError(Exception):
    pass


class AssistantListingAlreadyCreatedError(Exception):
    pass


class AssistantService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._assistant = AssistantRepository(db)
        self._roles = RoleRepository(db)
        self._areas = AreaService(AreaRepository(db))
        self._amenities = AmenityService(AmenityRepository(db))
        self._listings = ListingService(ListingRepository(db))

    def list_for_user(
        self,
        user_id: int,
    ) -> list[AssistantConversation]:
        return self._assistant.list_for_user(user_id)

    def create_conversation(
        self,
        user_id: int,
        assistant_role: AssistantRole,
    ) -> AssistantConversation:
        self._require_role(user_id, assistant_role)
        conversation = AssistantConversation(
            owner_user_id=user_id,
            assistant_role=assistant_role,
            workflow_state={},
        )
        self._assistant.add_conversation(conversation)
        self._commit()
        return conversation

    def get_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> tuple[AssistantConversation, list[AssistantMessage]]:
        conversation = self._get_owned(conversation_id, user_id)
        self._require_role(user_id, conversation.assistant_role)
        return conversation, self._assistant.list_messages(conversation_id)

    def send_message(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
    ) -> tuple[AssistantConversation, AssistantMessage]:
        content = content.strip()
        if not content or len(content) > 4000:
            raise ValueError("Message must contain 1 to 4,000 characters.")

        conversation = self._get_owned(conversation_id, user_id)
        self._require_role(user_id, conversation.assistant_role)
        previous_messages = self._assistant.list_messages(conversation_id)
        history = [
            {
                "role": (
                    "user" if message.sender_role == "user" else "assistant"
                ),
                "content": message.content,
            }
            for message in previous_messages[-20:]
        ]
        graph = build_assistant_graph(
            self._settings,
            self._listings,
            self._areas.list_areas(),
            self._amenities.list_amenities(),
        )
        result = graph.invoke(
            {
                "role": conversation.assistant_role,
                "message": content,
                "history": history,
                "workflow_state": dict(conversation.workflow_state),
            },
        )

        user_message = AssistantMessage(
            conversation_id=conversation_id,
            sender_role="user",
            content=content,
        )
        assistant_payload = {
            "listings": result.get("listings", []),
            "draft": result.get("draft"),
            "created_listing": result.get("created_listing"),
        }
        assistant_message = AssistantMessage(
            conversation_id=conversation_id,
            sender_role="assistant",
            content=result["response"],
            payload=assistant_payload,
        )
        conversation.workflow_state = result.get(
            "workflow_state",
            conversation.workflow_state,
        )
        conversation.updated_at = datetime.now()
        self._assistant.add_message(user_message)
        self._assistant.add_message(assistant_message)
        self._commit()
        return conversation, assistant_message

    def confirm_listing(
        self,
        conversation_id: int,
        user_id: int,
    ) -> tuple[AssistantConversation, ListingResponse]:
        conversation = self._get_owned(
            conversation_id,
            user_id,
            for_update=True,
        )
        self._require_role(user_id, "landlord")
        if conversation.assistant_role != "landlord":
            raise AssistantRolePermissionError(
                "Only landlord assistant conversations can create listings.",
            )

        workflow_state = dict(conversation.workflow_state)
        if workflow_state.get("created_listing_id") is not None:
            raise AssistantListingAlreadyCreatedError(
                "A listing has already been created for this conversation.",
            )

        draft = workflow_state.get("draft")
        if not isinstance(draft, dict) or not workflow_state.get(
            "amenities_answered",
        ):
            raise AssistantListingNotReadyError(
                "Complete the listing details before confirming.",
            )
        changes = ListingCreateRequest.model_validate(
            {
                key: draft[key]
                for key in ListingCreateRequest.model_fields
                if key in draft
            },
        )
        listing = LandlordListingService(self._db).create_listing(
            user_id,
            changes,
            commit=False,
        )
        workflow_state["created_listing_id"] = listing.listing_id
        conversation.workflow_state = workflow_state
        conversation.updated_at = datetime.now()
        self._assistant.add_message(
            AssistantMessage(
                conversation_id=conversation_id,
                sender_role="assistant",
                content=(
                    "Your listing has been saved as a draft. Add or update "
                    "photos and submit it for review from your landlord "
                    "dashboard when it is ready."
                ),
                payload={
                    "listings": [],
                    "draft": None,
                    "created_listing": listing.model_dump(mode="json"),
                },
            ),
        )
        self._commit()
        return conversation, listing

    def _require_role(
        self,
        user_id: int,
        required_role: Literal["tenant", "landlord"],
    ) -> None:
        roles = {role.name for role in self._roles.list_for_user(user_id)}
        if required_role not in roles:
            raise AssistantRolePermissionError(
                "You do not have permission to use this assistant.",
            )

    def _get_owned(
        self,
        conversation_id: int,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> AssistantConversation:
        conversation = self._assistant.get_for_user(
            conversation_id,
            user_id,
            for_update=for_update,
        )
        if conversation is None:
            raise AssistantConversationNotFoundError(
                "Assistant conversation not found.",
            )
        return conversation

    def _commit(self) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
