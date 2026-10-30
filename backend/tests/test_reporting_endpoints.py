import unittest
from datetime import datetime
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.reporting import (
    admin_dependency,
    get_report_service,
    router,
    tenant_dependency,
)
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.services.report_service import (
    ReportNotFoundError,
    ReportStateError,
    ReportTargetError,
)
from sqlalchemy.exc import SQLAlchemyError


class ReportingEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.app.dependency_overrides[get_db] = lambda: Mock()
        self.tenant = User(user_id=7)
        self.admin = User(user_id=4)
        self.app.dependency_overrides[tenant_dependency] = lambda: self.tenant
        self.app.dependency_overrides[admin_dependency] = lambda: self.admin
        self.service = Mock()
        self.app.dependency_overrides[get_report_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def report_payload(status: str = "open") -> dict[str, object]:
        return {
            "report_id": 5,
            "listing_id": 12,
            "target_user_id": None,
            "tenant_id": 7,
            "admin_id": None,
            "reason": "scam",
            "status": status,
            "details": "This listing appears suspicious.",
            "created_at": datetime(2026, 10, 1).isoformat(),
        }

    def test_tenant_can_submit_a_listing_report(self) -> None:
        self.service.submit_report.return_value = self.report_payload()

        response = self.client.post(
            "/api/v1/reports",
            json={
                "target": "listing",
                "listing_id": 12,
                "reason": "scam",
                "details": "This listing appears suspicious.",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.service.submit_report.assert_called_once()
        self.assertEqual(self.service.submit_report.call_args.args[0], 7)

    def test_report_form_requires_details(self) -> None:
        response = self.client.post(
            "/api/v1/reports",
            json={
                "target": "listing",
                "listing_id": 12,
                "reason": "scam",
                "details": "short",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.service.submit_report.assert_not_called()

    def test_tenant_can_view_only_their_own_reports(self) -> None:
        self.service.list_for_tenant.return_value = [self.report_payload()]

        response = self.client.get("/api/v1/users/me/reports")

        self.assertEqual(response.status_code, 200)
        self.service.list_for_tenant.assert_called_once_with(7)

    def test_admin_can_filter_report_queue_by_status(self) -> None:
        self.service.list_for_admin.return_value = [self.report_payload()]

        response = self.client.get(
            "/api/v1/admin/reports",
            params={"status": "open"},
        )

        self.assertEqual(response.status_code, 200)
        self.service.list_for_admin.assert_called_once_with("open")

    def test_admin_can_assign_report_to_themselves(self) -> None:
        self.service.assign_to_self.return_value = self.report_payload(
            status="under_review",
        )

        response = self.client.post("/api/v1/admin/reports/5/assign")

        self.assertEqual(response.status_code, 200)
        self.service.assign_to_self.assert_called_once_with(5, 4)

    def test_any_admin_can_resolve_report_with_note(self) -> None:
        self.service.resolve_report.return_value = self.report_payload(
            status="resolved",
        )

        response = self.client.post(
            "/api/v1/admin/reports/5/resolve",
            json={"note": "Reviewed and addressed."},
        )

        self.assertEqual(response.status_code, 200)
        self.service.resolve_report.assert_called_once_with(
            5,
            4,
            "Reviewed and addressed.",
        )

    def test_admin_can_dismiss_report(self) -> None:
        self.service.dismiss_report.return_value = self.report_payload(
            status="dismissed",
        )

        response = self.client.post(
            "/api/v1/admin/reports/5/dismiss",
            json={},
        )

        self.assertEqual(response.status_code, 200)
        self.service.dismiss_report.assert_called_once_with(5, 4, None)

    def test_report_state_error_maps_to_conflict(self) -> None:
        self.service.assign_to_self.side_effect = ReportStateError(
            "Only unassigned open reports can be assigned.",
        )

        response = self.client.post("/api/v1/admin/reports/5/assign")

        self.assertEqual(response.status_code, 409)

    def test_non_tenant_cannot_submit_reports(self) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)
        self.app.dependency_overrides[get_current_user] = lambda: User(
            user_id=9,
        )
        roles = Mock()
        roles.list_for_user.return_value = [Role(role_id=3, name="landlord")]

        from unittest.mock import patch

        with patch(
            "app.api.dependencies.RoleRepository",
            return_value=roles,
        ):
            response = self.client.post(
                "/api/v1/reports",
                json={
                    "target": "listing",
                    "listing_id": 12,
                    "reason": "scam",
                    "details": "This listing appears suspicious.",
                },
            )

        self.assertEqual(response.status_code, 403)
        self.service.submit_report.assert_not_called()

    def test_admin_route_requires_authentication_and_admin_role(self) -> None:
        self.app.dependency_overrides.pop(admin_dependency)
        self.app.dependency_overrides[get_current_user] = lambda: User(
            user_id=7,
        )
        roles = Mock()
        roles.list_for_user.return_value = [Role(role_id=1, name="tenant")]

        from unittest.mock import patch

        with patch(
            "app.api.dependencies.RoleRepository",
            return_value=roles,
        ):
            response = self.client.get("/api/v1/admin/reports")

        self.assertEqual(response.status_code, 403)
        self.service.list_for_admin.assert_not_called()

    def test_database_error_maps_to_service_unavailable(self) -> None:
        self.service.list_for_tenant.side_effect = SQLAlchemyError(
            "database unavailable",
        )

        response = self.client.get("/api/v1/users/me/reports")

        self.assertEqual(response.status_code, 503)

    def test_missing_report_maps_to_not_found(self) -> None:
        self.service.get_history.side_effect = ReportNotFoundError(
            "Report does not exist.",
        )

        response = self.client.get("/api/v1/admin/reports/999/history")

        self.assertEqual(response.status_code, 404)

    def test_self_report_error_maps_to_validation_error(self) -> None:
        self.service.submit_report.side_effect = ReportTargetError(
            "You cannot report your own account.",
        )

        response = self.client.post(
            "/api/v1/reports",
            json={
                "target": "user",
                "target_user_id": 7,
                "reason": "other",
                "details": "This is sufficiently detailed.",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
