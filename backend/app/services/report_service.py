from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.report import Report, ReportHistory
from app.models.user import User
from app.repositories.listing_repository import ListingRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services.listing_service import ListingService


class ReportNotFoundError(Exception):
    pass


class ReportTargetNotFoundError(Exception):
    pass


class ReportStateError(Exception):
    pass


class ReportTargetError(Exception):
    pass


class ReportService:
    OPEN_STATUS = "open"
    UNDER_REVIEW_STATUS = "under_review"
    RESOLVED_STATUS = "resolved"
    DISMISSED_STATUS = "dismissed"

    def __init__(self, db: Session) -> None:
        self._db = db
        self._reports = ReportRepository(db)
        self._listings = ListingRepository(db)
        self._users = UserRepository(db)
        self._public_listings = ListingService(self._listings)

    def submit_report(
        self,
        tenant_id: int,
        request: ReportCreateRequest,
    ) -> ReportResponse:
        listing = self._get_public_listing(request.listing_id)
        target_user_id = self._resolve_target_user_id(request, listing, tenant_id)
        report = Report(
            listing_id=request.listing_id,
            target_user_id=target_user_id,
            tenant_id=tenant_id,
            reason=request.reason,
            status=self.OPEN_STATUS,
            details=request.details,
        )
        try:
            self._reports.add(report)
            self._reports.add_history(
                report.report_id,
                tenant_id,
                "submitted",
            )
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        return ReportResponse.model_validate(report)

    def list_for_tenant(self, tenant_id: int) -> list[ReportResponse]:
        return [
            ReportResponse.model_validate(report)
            for report in self._reports.list_for_tenant(tenant_id)
        ]

    def list_for_admin(
        self,
        status_filter: str | None = None,
    ) -> list[ReportResponse]:
        return [
            ReportResponse.model_validate(report)
            for report in self._reports.list_for_admin(status_filter)
        ]

    def get_history(self, report_id: int) -> list[ReportHistory]:
        self._get_report(report_id)
        return self._reports.list_history(report_id)

    def assign_to_self(
        self,
        report_id: int,
        admin_id: int,
    ) -> ReportResponse:
        report = self._get_report(report_id, for_update=True)
        if report.status != self.OPEN_STATUS or report.admin_id is not None:
            raise ReportStateError("Only unassigned open reports can be assigned.")
        report.admin_id = admin_id
        report.status = self.UNDER_REVIEW_STATUS
        self._record_and_commit(report_id, admin_id, "assigned")
        return ReportResponse.model_validate(report)

    def resolve_report(
        self,
        report_id: int,
        admin_id: int,
        note: str | None = None,
    ) -> ReportResponse:
        return self._close_report(
            report_id,
            admin_id,
            self.RESOLVED_STATUS,
            "resolved",
            note,
        )

    def dismiss_report(
        self,
        report_id: int,
        admin_id: int,
        note: str | None = None,
    ) -> ReportResponse:
        return self._close_report(
            report_id,
            admin_id,
            self.DISMISSED_STATUS,
            "dismissed",
            note,
        )

    def _close_report(
        self,
        report_id: int,
        admin_id: int,
        new_status: str,
        action: str,
        note: str | None,
    ) -> ReportResponse:
        report = self._get_report(report_id, for_update=True)
        if report.status != self.UNDER_REVIEW_STATUS:
            raise ReportStateError(
                "Only reports under review can be resolved or dismissed.",
            )
        normalized_note = note.strip() if note is not None else None
        report.status = new_status
        self._record_and_commit(
            report_id,
            admin_id,
            action,
            normalized_note or None,
        )
        return ReportResponse.model_validate(report)

    def _record_and_commit(
        self,
        report_id: int,
        actor_user_id: int,
        action: str,
        note: str | None = None,
    ) -> None:
        try:
            self._reports.add_history(
                report_id,
                actor_user_id,
                action,
                note,
            )
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    def _get_report(
        self,
        report_id: int,
        *,
        for_update: bool = False,
    ) -> Report:
        report = self._reports.get_by_id(report_id, for_update=for_update)
        if report is None:
            raise ReportNotFoundError("Report does not exist.")
        return report

    def _get_public_listing(self, listing_id: int | None) -> Listing | None:
        if listing_id is None:
            return None
        if self._public_listings.get_public_listing(listing_id) is None:
            raise ReportTargetNotFoundError(
                "The listing is unavailable for reporting.",
            )
        return self._listings.get_by_id(listing_id)

    def _resolve_target_user_id(
        self,
        request: ReportCreateRequest,
        listing: Listing | None,
        tenant_id: int,
    ) -> int | None:
        if request.target == "listing":
            return None
        if request.target == "landlord":
            if listing is None:
                raise ReportTargetError(
                    "A landlord report must reference a public listing.",
                )
            target_user_id = listing.landlord_id
        else:
            target_user_id = request.target_user_id
            if target_user_id is None or self._users.get_by_id(target_user_id) is None:
                raise ReportTargetNotFoundError("The reported user does not exist.")

        if target_user_id == tenant_id:
            raise ReportTargetError("You cannot report your own account.")
        return target_user_id
