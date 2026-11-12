import unittest
from datetime import datetime
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints.saved_searches import (
    get_saved_search_service,
    tenant_dependency,
)
from app.api.v1.router import api_router
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.services.saved_search_service import SavedSearchWhatsAppNotEnabledError


class SavedSearchEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.tenant = User(user_id=6)
        self.app.dependency_overrides[get_saved_search_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[tenant_dependency] = lambda: self.tenant
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_saved_search() -> SavedSearch:
        return SavedSearch(
            saved_search_id=4,
            tenant_id=6,
            location="Rosebank",
            room_type="single_room",
            minimum_rent=1000,
            maximum_rent=5000,
            alerts_enabled=False,
            created_at=datetime(2026, 11, 2, 9, 0),
        )

    def test_create_saved_search_uses_authenticated_tenant(self) -> None:
        self.service.create_for_tenant.return_value = self.make_saved_search()

        response = self.client.post(
            "/api/v1/users/me/saved-searches",
            json={
                "location": "Rosebank",
                "room_type": "single_room",
                "minimum_rent": "1000.00",
                "maximum_rent": "5000.00",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["saved_search_id"], 4)
        self.assertNotIn("tenant_id", response.json())
        self.service.create_for_tenant.assert_called_once()
        self.assertEqual(
            self.service.create_for_tenant.call_args.args[0],
            self.tenant.user_id,
        )

    def test_create_saved_search_requires_at_least_one_filter(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/saved-searches",
            json={},
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_for_tenant.assert_not_called()

    def test_create_saved_search_rejects_inverted_rent_range(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/saved-searches",
            json={"minimum_rent": "5000.00", "maximum_rent": "1000.00"},
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_for_tenant.assert_not_called()

    def test_list_saved_searches_returns_only_safe_fields(self) -> None:
        self.service.list_for_tenant.return_value = [self.make_saved_search()]

        response = self.client.get("/api/v1/users/me/saved-searches")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["location"], "Rosebank")
        self.assertNotIn("tenant_id", response.json()[0])
        self.service.list_for_tenant.assert_called_once_with(
            self.tenant.user_id,
        )

    def test_list_saved_searches_handles_database_error(self) -> None:
        self.service.list_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        response = self.client.get("/api/v1/users/me/saved-searches")

        self.assertEqual(response.status_code, 503)

    def test_update_saved_search_alerts_uses_authenticated_tenant(self) -> None:
        saved_search = self.make_saved_search()
        saved_search.alerts_enabled = True
        self.service.update_alerts_for_tenant.return_value = saved_search

        response = self.client.patch(
            "/api/v1/users/me/saved-searches/4/alerts",
            json={"alerts_enabled": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["alerts_enabled"])
        self.service.update_alerts_for_tenant.assert_called_once()
        self.assertEqual(
            self.service.update_alerts_for_tenant.call_args.args[0:2],
            (self.tenant.user_id, 4),
        )

    def test_update_saved_search_alerts_returns_not_found_when_unowned(
        self,
    ) -> None:
        self.service.update_alerts_for_tenant.return_value = None

        response = self.client.patch(
            "/api/v1/users/me/saved-searches/4/alerts",
            json={"alerts_enabled": True},
        )

        self.assertEqual(response.status_code, 404)

    def test_update_saved_search_alerts_requires_whatsapp_consent(self) -> None:
        self.service.update_alerts_for_tenant.side_effect = (
            SavedSearchWhatsAppNotEnabledError("WhatsApp is not enabled.")
        )

        response = self.client.patch(
            "/api/v1/users/me/saved-searches/4/alerts",
            json={"alerts_enabled": True},
        )

        self.assertEqual(response.status_code, 409)

    def test_update_saved_search_alerts_handles_database_error(self) -> None:
        self.service.update_alerts_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        response = self.client.patch(
            "/api/v1/users/me/saved-searches/4/alerts",
            json={"alerts_enabled": False},
        )

        self.assertEqual(response.status_code, 503)

    def test_delete_saved_search_uses_authenticated_tenant(self) -> None:
        self.service.delete_for_tenant.return_value = True

        response = self.client.delete(
            "/api/v1/users/me/saved-searches/4",
        )

        self.assertEqual(response.status_code, 204)
        self.service.delete_for_tenant.assert_called_once_with(
            self.tenant.user_id,
            4,
        )

    def test_delete_saved_search_returns_not_found_when_not_owned(self) -> None:
        self.service.delete_for_tenant.return_value = False

        response = self.client.delete(
            "/api/v1/users/me/saved-searches/4",
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_saved_search_handles_database_error(self) -> None:
        self.service.delete_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        response = self.client.delete(
            "/api/v1/users/me/saved-searches/4",
        )

        self.assertEqual(response.status_code, 503)

    def test_saved_search_routes_require_tenant_role(self) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)

        response = self.client.get("/api/v1/users/me/saved-searches")

        self.assertEqual(response.status_code, 401)
        self.service.list_for_tenant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
