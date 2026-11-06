import json
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.whatsapp import (
    WhatsAppStatusResponse,
    WhatsAppVerificationConfirmRequest,
    WhatsAppVerificationStartRequest,
)
from app.services.whatsapp_provider import WhatsAppProviderError
from app.services.whatsapp_service import (
    WhatsAppService,
    WhatsAppVerificationError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])


def get_whatsapp_service(
    db: Session = Depends(get_db),
) -> WhatsAppService:
    return WhatsAppService(db)


@router.get(
    "/users/me/whatsapp",
    response_model=WhatsAppStatusResponse,
)
def get_whatsapp_status(
    current_user: User = Depends(get_current_user),
    service: WhatsAppService = Depends(get_whatsapp_service),
) -> WhatsAppStatusResponse:
    try:
        enabled = service.status_for_user(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("WhatsApp status could not be retrieved")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp preferences are temporarily unavailable.",
        ) from exc

    return WhatsAppStatusResponse(enabled=enabled)


@router.post(
    "/users/me/whatsapp/verification",
    status_code=status.HTTP_202_ACCEPTED,
)
def start_whatsapp_verification(
    request: WhatsAppVerificationStartRequest,
    current_user: User = Depends(get_current_user),
    service: WhatsAppService = Depends(get_whatsapp_service),
) -> dict[str, str]:
    try:
        service.start_verification(
            current_user.user_id,
            request.phone_number,
        )
    except WhatsAppVerificationError:
        logger.info("WhatsApp verification request was not eligible")
    except WhatsAppProviderError as exc:
        logger.exception("WhatsApp verification message could not be sent")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp verification is temporarily unavailable.",
        ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        logger.exception("WhatsApp verification could not be started")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp verification is temporarily unavailable.",
        ) from exc

    return {
        "detail": (
            "If eligible, a verification message will be sent. "
            "Please check the number or wait before trying again."
        ),
    }


@router.post(
    "/users/me/whatsapp/verification/confirm",
    response_model=WhatsAppStatusResponse,
)
def confirm_whatsapp_verification(
    request: WhatsAppVerificationConfirmRequest,
    current_user: User = Depends(get_current_user),
    service: WhatsAppService = Depends(get_whatsapp_service),
) -> WhatsAppStatusResponse:
    try:
        service.confirm_verification(current_user.user_id, request.code)
    except WhatsAppVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("WhatsApp verification could not be confirmed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp verification is temporarily unavailable.",
        ) from exc
    except RuntimeError as exc:
        logger.exception("WhatsApp verification configuration is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp verification is temporarily unavailable.",
        ) from exc

    return WhatsAppStatusResponse(enabled=True)


@router.delete(
    "/users/me/whatsapp",
    response_model=WhatsAppStatusResponse,
)
def unlink_whatsapp(
    current_user: User = Depends(get_current_user),
    service: WhatsAppService = Depends(get_whatsapp_service),
) -> WhatsAppStatusResponse:
    try:
        service.unlink(current_user.user_id)
    except SQLAlchemyError as exc:
        logger.exception("WhatsApp contact could not be unlinked")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp preferences are temporarily unavailable.",
        ) from exc

    return WhatsAppStatusResponse(enabled=False)


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    service: WhatsAppService = Depends(get_whatsapp_service),
    mode: Annotated[str, Query(alias="hub.mode")] = "",
    token: Annotated[str, Query(alias="hub.verify_token")] = "",
    challenge: Annotated[str, Query(alias="hub.challenge")] = "",
) -> PlainTextResponse:
    if not service.verify_webhook_challenge(mode, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification failed.",
        )
    return PlainTextResponse(challenge)


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    service: WhatsAppService = Depends(get_whatsapp_service),
    signature: Annotated[
        str | None,
        Header(alias="X-Hub-Signature-256"),
    ] = None,
) -> dict[str, str]:
    raw_body = await request.body()
    if not service.verify_webhook_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook signature is invalid.",
        )
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body is invalid.",
        )

    try:
        service.receive_webhook(payload)
    except SQLAlchemyError as exc:
        logger.exception("WhatsApp webhook could not be processed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook processing is temporarily unavailable.",
        ) from exc
    except RuntimeError as exc:
        logger.exception("WhatsApp webhook configuration is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook processing is temporarily unavailable.",
        ) from exc
    return {"status": "ok"}
