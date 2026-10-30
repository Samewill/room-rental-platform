import logging
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import (
    ReportCreateRequest,
    ReportHistoryResponse,
    ReportResolutionRequest,
    ReportResponse,
)
from app.services.report_service import (
    ReportNotFoundError,
    ReportService,
    ReportStateError,
    ReportTargetError,
    ReportTargetNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["reporting"])
tenant_dependency = require_role("tenant")
admin_dependency = require_role("admin")


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


def _raise_report_http_error(
    error: Exception,
    report_id: int | None = None,
) -> NoReturn:
    if isinstance(error, (ReportNotFoundError, ReportTargetNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, ReportStateError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    if isinstance(error, ReportTargetError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    logger.exception("Report request failed for report %s", report_id)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Reporting is temporarily unavailable.",
    ) from error


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_report(
    request: ReportCreateRequest,
    current_tenant: User = Depends(tenant_dependency),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    try:
        return service.submit_report(current_tenant.user_id, request)
    except (
        ReportTargetError,
        ReportTargetNotFoundError,
        SQLAlchemyError,
    ) as exc:
        _raise_report_http_error(exc)


@router.get(
    "/users/me/reports",
    response_model=list[ReportResponse],
)
def list_my_reports(
    current_tenant: User = Depends(tenant_dependency),
    service: ReportService = Depends(get_report_service),
) -> list[ReportResponse]:
    try:
        return service.list_for_tenant(current_tenant.user_id)
    except SQLAlchemyError as exc:
        _raise_report_http_error(exc)


@router.get(
    "/admin/reports",
    response_model=list[ReportResponse],
)
def list_admin_reports(
    report_status: Annotated[
        str | None,
        Query(alias="status", pattern="^(open|under_review|resolved|dismissed)$"),
    ] = None,
    current_admin: User = Depends(admin_dependency),
    service: ReportService = Depends(get_report_service),
) -> list[ReportResponse]:
    try:
        return service.list_for_admin(report_status)
    except SQLAlchemyError as exc:
        _raise_report_http_error(exc)


@router.get(
    "/admin/reports/{report_id}/history",
    response_model=list[ReportHistoryResponse],
)
def get_report_history(
    report_id: Annotated[int, Path(gt=0)],
    current_admin: User = Depends(admin_dependency),
    service: ReportService = Depends(get_report_service),
) -> list[ReportHistoryResponse]:
    try:
        return service.get_history(report_id)
    except (ReportNotFoundError, SQLAlchemyError) as exc:
        _raise_report_http_error(exc, report_id)


@router.post(
    "/admin/reports/{report_id}/assign",
    response_model=ReportResponse,
)
def assign_report(
    report_id: Annotated[int, Path(gt=0)],
    current_admin: User = Depends(admin_dependency),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    try:
        return service.assign_to_self(report_id, current_admin.user_id)
    except (ReportNotFoundError, ReportStateError, SQLAlchemyError) as exc:
        _raise_report_http_error(exc, report_id)


@router.post(
    "/admin/reports/{report_id}/resolve",
    response_model=ReportResponse,
)
def resolve_report(
    report_id: Annotated[int, Path(gt=0)],
    request: ReportResolutionRequest,
    current_admin: User = Depends(admin_dependency),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    try:
        return service.resolve_report(
            report_id,
            current_admin.user_id,
            request.note,
        )
    except (ReportNotFoundError, ReportStateError, SQLAlchemyError) as exc:
        _raise_report_http_error(exc, report_id)


@router.post(
    "/admin/reports/{report_id}/dismiss",
    response_model=ReportResponse,
)
def dismiss_report(
    report_id: Annotated[int, Path(gt=0)],
    request: ReportResolutionRequest,
    current_admin: User = Depends(admin_dependency),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    try:
        return service.dismiss_report(
            report_id,
            current_admin.user_id,
            request.note,
        )
    except (ReportNotFoundError, ReportStateError, SQLAlchemyError) as exc:
        _raise_report_http_error(exc, report_id)
