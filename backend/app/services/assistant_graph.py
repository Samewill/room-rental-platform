import json
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any, Literal, TypedDict

import httpx
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.schemas.amenity import AmenityResponse
from app.schemas.area import AreaResponse
from app.schemas.landlord_listing import ListingCreateRequest
from app.schemas.listing import ListingResponse
from app.services.listing_service import ListingService


logger = logging.getLogger(__name__)


class AssistantProviderError(Exception):
    pass


class TenantCriteria(BaseModel):
    location: str | None = Field(default=None, max_length=150)
    room_type: Literal[
        "single_room",
        "shared_room",
        "bachelor_flat",
        "self_contained",
    ] | None = None
    minimum_rent: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    maximum_rent: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    amenities: list[str] = Field(default_factory=list, max_length=10)
    available_by: date | None = None


class TenantTurn(BaseModel):
    intent: Literal["search", "listing_question", "general"]
    listing_id: int | None = Field(default=None, gt=0)
    criteria: TenantCriteria = Field(default_factory=TenantCriteria)
    clear_criteria: list[
        Literal[
            "location",
            "room_type",
            "minimum_rent",
            "maximum_rent",
            "amenities",
            "available_by",
        ]
    ] = Field(default_factory=list)


class LandlordTurn(BaseModel):
    area_name: str | None = Field(default=None, max_length=150)
    title: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, min_length=1)
    room_type: Literal[
        "single_room",
        "shared_room",
        "bachelor_flat",
        "self_contained",
    ] | None = None
    monthly_rent: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    deposit_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    address: str | None = Field(default=None, max_length=255)
    date_available: date | None = None
    amenities: list[str] | None = None
    amenities_answered: bool | None = None


class AssistantGraphState(TypedDict, total=False):
    role: Literal["tenant", "landlord"]
    message: str
    history: list[dict[str, str]]
    workflow_state: dict[str, Any]
    intent: str
    response: str
    listings: list[dict[str, Any]]
    draft: dict[str, Any] | None
    created_listing: dict[str, Any] | None
    listing_id: int | None
    next_node: str


def _jsonable_criteria(criteria: TenantCriteria) -> dict[str, Any]:
    return {
        "location": criteria.location,
        "room_type": criteria.room_type,
        "minimum_rent": (
            str(criteria.minimum_rent)
            if criteria.minimum_rent is not None
            else None
        ),
        "maximum_rent": (
            str(criteria.maximum_rent)
            if criteria.maximum_rent is not None
            else None
        ),
        "amenities": criteria.amenities,
        "available_by": (
            criteria.available_by.isoformat()
            if criteria.available_by is not None
            else None
        ),
    }


def _call_provider(
    provider: str,
    api_key: str,
    model: str,
    max_tokens: int,
    base_url: str,
    timeout: float,
    system_prompt: str,
    history: list[dict[str, str]],
    response_model: type[BaseModel],
) -> BaseModel:
    messages = [
        {"role": "system", "content": system_prompt},
        *history[-20:],
    ]
    endpoint = (
        "https://api.groq.com/openai/v1/chat/completions"
        if provider == "groq"
        else f"{base_url.rstrip('/')}/chat/completions"
    )
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("The model response did not contain text.")
    return response_model.model_validate(json.loads(content))


def complete_json(
    settings: Settings,
    system_prompt: str,
    history: list[dict[str, str]],
    message: str,
    response_model: type[BaseModel],
) -> BaseModel:
    providers: list[tuple[str, str, str, int, str]] = []
    inception_key = (
        settings.inception_api_key.get_secret_value().strip()
        if settings.inception_api_key is not None
        else ""
    )
    groq_key = (
        settings.groq_api_key.get_secret_value().strip()
        if settings.groq_api_key is not None
        else ""
    )
    if inception_key:
        providers.append(
            (
                "inception",
                inception_key,
                settings.inception_model,
                settings.inception_max_retries + 1,
                settings.inception_base_url,
            ),
        )
    if groq_key:
        providers.append(
            (
                "groq",
                groq_key,
                settings.groq_model,
                1,
                "https://api.groq.com/openai/v1",
            ),
        )
    if not providers:
        raise AssistantProviderError(
            "Configure INCEPTION_API_KEY or GROQ_API_KEY for the AI assistant.",
        )

    request_history = [*history[-20:], {"role": "user", "content": message}]
    last_error: Exception | None = None
    for provider, api_key, model, attempts, base_url in providers:
        for attempt in range(attempts):
            try:
                token_limit = (
                    settings.inception_max_tokens
                    if provider == "inception"
                    else settings.groq_max_tokens
                )
                return _call_provider(
                    provider,
                    api_key,
                    model,
                    token_limit,
                    base_url,
                    settings.llm_call_timeout_seconds,
                    system_prompt,
                    request_history,
                    response_model,
                )
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                IndexError,
                TypeError,
                ValidationError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "AI provider %s failed on attempt %s (%s)",
                    provider,
                    attempt + 1,
                    type(exc).__name__,
                )
                if provider == "inception" and attempt + 1 < attempts:
                    delay = min(
                        settings.inception_backoff_base_seconds * (2**attempt),
                        settings.inception_backoff_max_seconds,
                    )
                    time.sleep(delay)

    raise AssistantProviderError(
        "The configured AI providers could not complete the request.",
    ) from last_error


def _normalise(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _normalise_amenity(value: str, available: set[str]) -> str | None:
    normalized = _normalise(value)
    if normalized in {"wifi", "wi fi"}:
        normalized = "wi fi"
    return next(
        (
            amenity
            for amenity in available
            if _normalise(amenity) == normalized
        ),
        None,
    )


def _public_listing_payload(
    listing: ListingResponse,
    area_names: dict[int, str],
) -> dict[str, Any]:
    return {
        "listing": listing.model_dump(mode="json"),
        "area_name": area_names.get(listing.area_id, "Area unavailable"),
    }


def build_assistant_graph(
    settings: Settings,
    listing_service: ListingService,
    areas: list[AreaResponse],
    amenities: list[AmenityResponse],
) -> Any:
    area_names = {area.area_id: area.name for area in areas}
    available_amenities = {amenity.name for amenity in amenities}

    def route_role(state: AssistantGraphState) -> dict[str, str]:
        return {
            "next_node": (
                "tenant_understand"
                if state["role"] == "tenant"
                else "landlord_collect"
            ),
        }

    def tenant_understand(state: AssistantGraphState) -> dict[str, Any]:
        current_criteria = TenantCriteria.model_validate(
            state["workflow_state"].get("criteria", {}),
        )
        prompt = (
            "You extract room-search intent for a South African room-rental "
            "platform. Return JSON with keys intent (search, listing_question, "
            "or general), listing_id (positive integer or null), and criteria "
            "(location, room_type, minimum_rent, maximum_rent, amenities, "
            "available_by), and clear_criteria (names of criteria the user "
            "explicitly removed). Extract only what the user actually said; "
            "preserve known criteria unless the user changes them. Use ZAR "
            "amounts as numbers, ISO dates, exact amenity names when possible, "
            "and null for unknown values. Never invent listing details. Available "
            f"amenities: {sorted(available_amenities)}. Existing criteria: "
            f"{current_criteria.model_dump(mode='json')}. Last displayed "
            f"listing IDs in order: "
            f"{state['workflow_state'].get('last_listing_ids', [])}. Use those "
            "IDs only to resolve references such as 'the first room'. Today's "
            f"date: {date.today().isoformat()}."
        )
        turn = complete_json(
            settings,
            prompt,
            state.get("history", []),
            state["message"],
            TenantTurn,
        )
        assert isinstance(turn, TenantTurn)
        criteria = current_criteria.model_dump()
        criteria.update(
            {
                key: value
                for key, value in turn.criteria.model_dump().items()
                if value is not None and value != []
            },
        )
        for field in turn.clear_criteria:
            if field == "amenities" and turn.criteria.amenities:
                continue
            criteria[field] = [] if field == "amenities" else None
        if turn.criteria.amenities:
            criteria["amenities"] = turn.criteria.amenities
        elif "amenities" not in turn.clear_criteria:
            criteria["amenities"] = current_criteria.amenities
        criteria_model = TenantCriteria.model_validate(criteria)
        next_node = {
            "search": "tenant_search",
            "listing_question": "tenant_listing_question",
            "general": "tenant_general",
        }[turn.intent]
        workflow_state = dict(state["workflow_state"])
        workflow_state["criteria"] = _jsonable_criteria(criteria_model)
        return {
            "intent": turn.intent,
            "workflow_state": workflow_state,
            "next_node": next_node,
            "listing_id": turn.listing_id,
        }

    def tenant_search(state: AssistantGraphState) -> dict[str, Any]:
        criteria = TenantCriteria.model_validate(
            state["workflow_state"].get("criteria", {}),
        )
        location = _normalise(criteria.location or "")
        minimum_rent = criteria.minimum_rent
        maximum_rent = criteria.maximum_rent
        required_amenities = {
            canonical
            for item in criteria.amenities
            if (canonical := _normalise_amenity(item, available_amenities))
            is not None
        }
        unsupported_amenities = [
            item
            for item in criteria.amenities
            if _normalise_amenity(item, available_amenities) is None
        ]
        matches = []
        for listing in listing_service.list_public_listings():
            if unsupported_amenities:
                break
            area_name = area_names.get(listing.area_id, "")
            if location and location not in _normalise(
                f"{area_name} {listing.address} {listing.title} "
                f"{listing.description}",
            ):
                continue
            if (
                criteria.room_type is not None
                and listing.room_type != criteria.room_type
            ):
                continue
            rent = listing.monthly_rent
            if minimum_rent is not None and rent < minimum_rent:
                continue
            if maximum_rent is not None and rent > maximum_rent:
                continue
            if not required_amenities.issubset(set(listing.amenities)):
                continue
            if (
                criteria.available_by is not None
                and listing.date_available > criteria.available_by
            ):
                continue
            matches.append(listing)

        matches.sort(
            key=lambda listing: (listing.monthly_rent, listing.listing_id),
        )
        shown = matches[:8]
        if unsupported_amenities:
            response = (
                "The platform does not currently list "
                f"{', '.join(unsupported_amenities)} as supported amenities. "
                "I haven't shown rooms that might not match. Supported options "
                f"are: {', '.join(sorted(available_amenities))}."
            )
        elif matches:
            response = (
                f"I found {len(matches)} verified room"
                f"{'' if len(matches) == 1 else 's'} matching those details."
            )
        else:
            response = (
                "I couldn't find published rooms matching those details. "
                "You can try a different area, budget, or amenity."
            )
        follow_up = []
        if not location:
            follow_up.append("the area or suburb")
        if minimum_rent is None and maximum_rent is None:
            follow_up.append("your monthly budget")
        if criteria.room_type is None:
            follow_up.append("your preferred room type")
        if follow_up:
            response += (
                " To narrow the search, please share "
                + ", ".join(follow_up[:-1])
                + (" and " if len(follow_up) > 1 else "")
                + follow_up[-1]
                + "."
            )
        workflow_state = dict(state["workflow_state"])
        workflow_state["last_listing_ids"] = [
            listing.listing_id for listing in shown
        ]
        return {
            "response": response,
            "listings": [
                _public_listing_payload(listing, area_names)
                for listing in shown
            ],
            "workflow_state": workflow_state,
        }

    def tenant_listing_question(
        state: AssistantGraphState,
    ) -> dict[str, Any]:
        listing_id = state.get("listing_id")
        listing = (
            listing_service.get_public_listing(listing_id)
            if listing_id is not None
            else None
        )
        if listing is None:
            response = (
                "I can answer questions using published platform listings. "
                "Please share the listing's ID or search for it first."
            )
            return {"response": response, "listings": []}

        result = _public_listing_payload(listing, area_names)
        return {
            "response": (
                "Here are the verified details currently available for this "
                "listing. Availability and prices are shown as recorded on "
                "the platform; contact the landlord to confirm any changes."
            ),
            "listings": [result],
        }

    def tenant_general(state: AssistantGraphState) -> dict[str, str]:
        return {
            "response": (
                "I can help you find rooms using the platform's published "
                "listings. Tell me the area, room type, budget, or amenities "
                "you need."
            ),
        }

    def landlord_collect(state: AssistantGraphState) -> dict[str, Any]:
        current_draft = dict(state["workflow_state"].get("draft", {}))
        prompt = (
            "You collect a landlord's room-listing details. Return JSON with "
            "optional fields area_name, title, description, room_type, "
            "monthly_rent, deposit_amount, address, date_available, "
            "amenities, and amenities_answered. Extract only details explicitly "
            "provided by the landlord; do not infer location, price, room "
            "type, deposit, address, or availability. Preserve existing values "
            "unless corrected. room_type must be one of single_room, "
            "shared_room, bachelor_flat, self_contained. Amenities must use "
            "the available exact names. Set amenities_answered true if the "
            "landlord has listed amenities or said there are none. Otherwise "
            "leave it null. Dates must be ISO YYYY-MM-DD. Today's date is "
            f"{date.today().isoformat()}. Existing draft: {current_draft}. "
            f"Available areas: {[area.name for area in areas]}. "
            f"Available amenities: {sorted(available_amenities)}."
        )
        turn = complete_json(
            settings,
            prompt,
            state.get("history", []),
            state["message"],
            LandlordTurn,
        )
        assert isinstance(turn, LandlordTurn)
        workflow_state = dict(state["workflow_state"])

        area_name = turn.area_name.strip() if turn.area_name else None
        if area_name is not None:
            area = next(
                (
                    item
                    for item in areas
                    if _normalise(item.name) == _normalise(area_name)
                ),
                None,
            )
            if area is not None:
                current_draft["area_id"] = area.area_id
                current_draft["area_name"] = area.name
            else:
                current_draft["area_id"] = None
                current_draft["area_name"] = area_name

        for field in (
            "title",
            "description",
            "room_type",
            "monthly_rent",
            "deposit_amount",
            "address",
            "date_available",
        ):
            value = getattr(turn, field)
            if value is not None:
                current_draft[field] = (
                    str(value)
                    if isinstance(value, (date, Decimal))
                    else value.strip()
                    if isinstance(value, str)
                    else value
                )

        if turn.amenities is not None:
            accepted = {
                canonical
                for item in turn.amenities
                if (
                    canonical := _normalise_amenity(
                        item,
                        available_amenities,
                    )
                )
                is not None
            }
            current_draft["amenities"] = sorted(accepted)
            workflow_state["unsupported_amenities"] = [
                item
                for item in turn.amenities
                if _normalise_amenity(item, available_amenities) is None
            ]
            if workflow_state["unsupported_amenities"]:
                workflow_state["amenities_answered"] = False
        else:
            current_draft.setdefault("amenities", [])

        if (
            not workflow_state.get("unsupported_amenities")
            and (turn.amenities_answered is True or turn.amenities)
        ):
            workflow_state["amenities_answered"] = True

        workflow_state["draft"] = current_draft
        missing_fields = _missing_listing_fields(
            current_draft,
            workflow_state.get("amenities_answered", False),
        )
        if missing_fields:
            if (
                missing_fields[0] == "amenities"
                and workflow_state.get("unsupported_amenities")
            ):
                response = (
                    "The platform does not currently list "
                    f"{', '.join(workflow_state['unsupported_amenities'])} "
                    "as supported amenities. Please choose from: "
                    f"{', '.join(sorted(available_amenities))}, or say none."
                )
            else:
                response = _landlord_follow_up(
                    missing_fields,
                    current_draft.get("area_name"),
                    [area.name for area in areas],
                    sorted(available_amenities),
                )
            draft_payload = {
                **current_draft,
                "missing_fields": missing_fields,
                "ready_to_confirm": False,
            }
        else:
            current_draft.setdefault("google_place_id", None)
            current_draft.setdefault("latitude", None)
            current_draft.setdefault("longitude", None)
            validated = ListingCreateRequest.model_validate(
                {
                    key: current_draft[key]
                    for key in ListingCreateRequest.model_fields
                },
            )
            current_draft = validated.model_dump(mode="json")
            current_draft["area_name"] = area_names[current_draft["area_id"]]
            workflow_state["draft"] = current_draft
            response = (
                "I have collected the required details. Add any photos you "
                "want to include, review the summary, then confirm to save "
                "this as a draft listing. It will not be published until you "
                "submit it for review."
            )
            draft_payload = {
                **current_draft,
                "missing_fields": [],
                "ready_to_confirm": True,
            }
        return {
            "workflow_state": workflow_state,
            "response": response,
            "draft": draft_payload,
        }

    def route_after_role(state: AssistantGraphState) -> str:
        return state["next_node"]

    graph = StateGraph(AssistantGraphState)
    graph.add_node("route_role", route_role)
    graph.add_node("tenant_understand", tenant_understand)
    graph.add_node("tenant_search", tenant_search)
    graph.add_node("tenant_listing_question", tenant_listing_question)
    graph.add_node("tenant_general", tenant_general)
    graph.add_node("landlord_collect", landlord_collect)
    graph.add_edge(START, "route_role")
    graph.add_conditional_edges(
        "route_role",
        route_after_role,
        {
            "tenant_understand": "tenant_understand",
            "landlord_collect": "landlord_collect",
        },
    )
    graph.add_conditional_edges(
        "tenant_understand",
        route_after_role,
        {
            "tenant_search": "tenant_search",
            "tenant_listing_question": "tenant_listing_question",
            "tenant_general": "tenant_general",
        },
    )
    for node in (
        "tenant_search",
        "tenant_listing_question",
        "tenant_general",
        "landlord_collect",
    ):
        graph.add_edge(node, END)
    return graph.compile()


def _missing_listing_fields(
    draft: dict[str, Any],
    amenities_answered: bool,
) -> list[str]:
    required = (
        ("area_id", "area"),
        ("room_type", "room type"),
        ("monthly_rent", "monthly rent"),
        ("deposit_amount", "deposit amount"),
        ("address", "street address"),
        ("date_available", "availability date"),
        ("title", "listing title"),
        ("description", "description"),
    )
    missing = [
        label
        for field, label in required
        if draft.get(field) in (None, "")
    ]
    if not amenities_answered:
        missing.append("amenities")
    return missing


def _landlord_follow_up(
    missing_fields: list[str],
    area_value: str | None,
    available_areas: list[str],
    available_amenities: list[str],
) -> str:
    next_field = missing_fields[0]
    if next_field == "area":
        if area_value:
            return (
                f"I couldn't match '{area_value}' to a platform area. "
                f"Please choose one of: {', '.join(available_areas)}."
            )
        return (
            "Which area is the room in? Please choose from: "
            f"{', '.join(available_areas)}."
        )
    questions = {
        "room type": (
            "What type of room is it: single room, shared room, bachelor flat, "
            "or self-contained?"
        ),
        "monthly rent": "What is the monthly rent in rand?",
        "deposit amount": "What deposit amount should the listing show?",
        "street address": "What street address should the listing show?",
        "availability date": "On what date will the room be available?",
        "listing title": "What title should appear on the listing?",
        "description": "How would you describe the room and property?",
        "amenities": (
            "Which amenities are included, if any? Available options are: "
            f"{', '.join(available_amenities)}. You can also say none."
        ),
    }
    return questions[next_field]
