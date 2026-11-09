import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.areas import get_area_service
from app.api.v1.router import api_router
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.area import AreaResponse


class AreaEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.app.dependency_overrides[get_area_service] = (
            lambda: self.service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_areas_returns_service_results(self) -> None:
        self.service.list_areas.return_value = [
            AreaResponse(area_id=1, name="Braamfontein"),
            AreaResponse(area_id=2, name="Melville"),
        ]

        response = self.client.get("/api/v1/areas")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"area_id": 1, "name": "Braamfontein"},
                {"area_id": 2, "name": "Melville"},
            ],
        )
        self.service.list_areas.assert_called_once_with()

    def test_list_areas_returns_empty_list_when_no_areas_exist(self) -> None:
        self.service.list_areas.return_value = []

        response = self.client.get("/api/v1/areas")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_search_areas_passes_query_and_limit(self) -> None:
        self.service.search_areas.return_value = [
            AreaResponse(area_id=1, name="Glenwood"),
        ]

        response = self.client.get("/api/v1/areas?search=glen&limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Glenwood")
        self.service.search_areas.assert_called_once_with("glen", 5)

    def test_search_areas_rejects_whitespace_only_query(self) -> None:
        response = self.client.get("/api/v1/areas?search=%20%20")

        self.assertEqual(response.status_code, 422)
        self.service.search_areas.assert_not_called()
        self.service.list_areas.assert_not_called()

    def test_resolve_area_requires_landlord_authentication(self) -> None:
        response = self.client.post(
            "/api/v1/areas/resolve",
            json={"name": "Newtown"},
        )

        self.assertEqual(response.status_code, 401)
        self.service.resolve_area.assert_not_called()

    def test_landlord_can_resolve_an_arbitrary_area_name(self) -> None:
        self.service.resolve_area.return_value = AreaResponse(
            area_id=3,
            name="Newtown",
        )
        self.app.dependency_overrides[get_current_user] = lambda: User(
            user_id=8,
        )
        self.app.dependency_overrides[get_db] = lambda: Mock()
        role_repository = Mock()
        role_repository.list_for_user.return_value = [
            Role(role_id=1, name="landlord"),
        ]

        with patch(
            "app.api.dependencies.RoleRepository",
            return_value=role_repository,
        ):
            response = self.client.post(
                "/api/v1/areas/resolve",
                json={"name": "  Newtown  "},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"area_id": 3, "name": "Newtown"})
        self.service.resolve_area.assert_called_once_with("Newtown")

    def test_list_areas_returns_service_unavailable_on_database_error(
        self,
    ) -> None:
        self.service.list_areas.side_effect = SQLAlchemyError(
            "database unavailable",
        )

        response = self.client.get("/api/v1/areas")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Area data is temporarily unavailable.",
        )


if __name__ == "__main__":
    unittest.main()
