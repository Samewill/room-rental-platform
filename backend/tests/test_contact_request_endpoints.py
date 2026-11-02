import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints.contact_requests import (
    get_contact_request_service,
    landlord_dependency,
    tenant_dependency,
)
from app.api.dependencies import get_current_user
from app.api.v1.router import api_router
from app.db.session import get_db
from app.models.contact_request import ContactRequest
from app.models.user import User
from app.services.contact_request_service import (
    ContactRequestForbiddenError,
    ContactRequestListingUnavailableError,
    ContactRequestNotFoundError,
    ContactRequestStateError,
)


class ContactRequestEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.tenant = User(user_id=6)
        self.landlord = User(user_id=8)
        self.app.dependency_overrides[get_contact_request_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[tenant_dependency] = lambda: self.tenant
        self.app.dependency_overrides[landlord_dependency] = (
            lambda: self.landlord
        )
        self.user = self.landlord
        self.db = Mock()
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_request() -> ContactRequest:
        return ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
            requested_at=datetime(2026, 10, 30, 8, 0),
        )

    @staticmethod
    def make_role(name: str) -> SimpleNamespace:
        return SimpleNamespace(name=name)

    def test_create_contact_request_uses_authenticated_tenant(self) -> None:
        self.service.create_request.return_value = self.make_request()

        response = self.client.post(
            "/api/v1/listings/14/contact-requests",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "request_id": 5,
                "listing_id": 14,
                "status": "pending",
                "requested_at": "2026-10-30T08:00:00",
            },
        )
        self.service.create_request.assert_called_once_with(6, 14)

    def test_list_my_contact_requests_uses_authenticated_tenant(self) -> None:
        self.service.list_for_tenant.return_value = [self.make_request()]

        response = self.client.get("/api/v1/users/me/contact-requests")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "request_id": 5,
                    "listing_id": 14,
                    "status": "pending",
                    "requested_at": "2026-10-30T08:00:00",
                },
            ],
        )
        self.service.list_for_tenant.assert_called_once_with(6)

    def test_list_my_contact_requests_returns_empty_list(self) -> None:
        self.service.list_for_tenant.return_value = []

        response = self.client.get("/api/v1/users/me/contact-requests")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_my_contact_requests_requires_tenant_authentication(
        self,
    ) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.get("/api/v1/users/me/contact-requests")

        self.assertEqual(response.status_code, 401)
        self.service.list_for_tenant.assert_not_called()

    def test_list_my_contact_requests_handles_database_error(self) -> None:
        self.service.list_for_tenant.side_effect = SQLAlchemyError(
            "database failure"
        )

        response = self.client.get("/api/v1/users/me/contact-requests")

        self.assertEqual(response.status_code, 503)

    def test_list_received_requests_uses_authenticated_landlord(self) -> None:
        self.service.list_for_landlord.return_value = [self.make_request()]

        response = self.client.get(
            "/api/v1/users/me/received-requests",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "request_id": 5,
                    "listing_id": 14,
                    "status": "pending",
                    "requested_at": "2026-10-30T08:00:00",
                },
            ],
        )
        self.service.list_for_landlord.assert_called_once_with(8)

    def test_list_received_requests_returns_empty_list(self) -> None:
        self.service.list_for_landlord.return_value = []

        response = self.client.get(
            "/api/v1/users/me/received-requests",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_received_requests_requires_landlord_authentication(
        self,
    ) -> None:
        self.app.dependency_overrides.pop(landlord_dependency)
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.get(
            "/api/v1/users/me/received-requests",
        )

        self.assertEqual(response.status_code, 401)
        self.service.list_for_landlord.assert_not_called()

    def test_list_received_requests_handles_database_error(self) -> None:
        self.service.list_for_landlord.side_effect = SQLAlchemyError(
            "database failure"
        )

        response = self.client.get(
            "/api/v1/users/me/received-requests",
        )

        self.assertEqual(response.status_code, 503)

    def test_create_response_does_not_expose_tenant_contact_details(
        self,
    ) -> None:
        self.service.create_request.return_value = self.make_request()

        response = self.client.post(
            "/api/v1/listings/14/contact-requests",
        )

        self.assertEqual(
            set(response.json()),
            {"request_id", "listing_id", "status", "requested_at"},
        )
        self.assertNotIn("tenant_id", response.json())
        self.assertNotIn("email", response.json())
        self.assertNotIn("phone_no", response.json())

    def test_create_contact_request_requires_tenant_authentication(
        self,
    ) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.post(
            "/api/v1/listings/14/contact-requests",
        )

        self.assertEqual(response.status_code, 401)
        self.service.create_request.assert_not_called()

    def test_create_contact_request_rejects_nonpositive_listing_id(
        self,
    ) -> None:
        response = self.client.post(
            "/api/v1/listings/0/contact-requests",
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_request.assert_not_called()

    def test_create_contact_request_returns_not_found_for_unavailable_listing(
        self,
    ) -> None:
        self.service.create_request.side_effect = (
            ContactRequestListingUnavailableError()
        )

        response = self.client.post(
            "/api/v1/listings/14/contact-requests",
        )

        self.assertEqual(response.status_code, 404)

    def test_create_contact_request_returns_service_unavailable_on_database_error(
        self,
    ) -> None:
        self.service.create_request.side_effect = SQLAlchemyError(
            "database failure"
        )

        response = self.client.post(
            "/api/v1/listings/14/contact-requests",
        )

        self.assertEqual(response.status_code, 503)

    def test_landlord_can_approve_contact_request(self) -> None:
        contact_request = self.make_request()
        contact_request.status = "approved"
        self.service.update_status.return_value = contact_request
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")
        self.service.update_status.assert_called_once_with(8, 5, "approved")

    def test_tenant_can_cancel_own_contact_request(self) -> None:
        self.user = self.tenant
        contact_request = self.make_request()
        contact_request.status = "cancelled"
        self.service.update_status.return_value = contact_request
        self.db.scalars.return_value.all.return_value = [
            self.make_role("tenant")
        ]

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "cancelled"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")
        self.service.update_status.assert_called_once_with(6, 5, "cancelled")

    def test_tenant_cannot_approve_contact_request(self) -> None:
        self.user = self.tenant
        self.db.scalars.return_value.all.return_value = [
            self.make_role("tenant")
        ]

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 403)
        self.service.update_status.assert_not_called()

    def test_landlord_cannot_cancel_tenant_contact_request(self) -> None:
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "cancelled"},
        )

        self.assertEqual(response.status_code, 403)
        self.service.update_status.assert_not_called()

    def test_invalid_contact_request_status_is_rejected(self) -> None:
        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "pending"},
        )

        self.assertEqual(response.status_code, 422)
        self.service.update_status.assert_not_called()

    def test_contact_request_update_requires_authentication(self) -> None:
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 401)
        self.service.update_status.assert_not_called()

    def test_contact_request_update_maps_ownership_failure(self) -> None:
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]
        self.service.update_status.side_effect = ContactRequestForbiddenError()

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 403)

    def test_contact_request_update_maps_missing_request(self) -> None:
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]
        self.service.update_status.side_effect = ContactRequestNotFoundError()

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 404)

    def test_contact_request_update_maps_invalid_state(self) -> None:
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]
        self.service.update_status.side_effect = ContactRequestStateError()

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 409)

    def test_contact_request_update_maps_role_lookup_database_error(self) -> None:
        self.db.scalars.side_effect = SQLAlchemyError("database failure")

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 503)

    def test_contact_request_update_maps_service_database_error(self) -> None:
        self.db.scalars.return_value.all.return_value = [
            self.make_role("landlord")
        ]
        self.service.update_status.side_effect = SQLAlchemyError(
            "database failure"
        )

        response = self.client.patch(
            "/api/v1/contact-requests/5",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
