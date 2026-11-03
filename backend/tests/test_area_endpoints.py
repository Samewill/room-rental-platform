import unittest
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints.areas import get_area_service
from app.api.v1.router import api_router
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
