import unittest
from datetime import datetime
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints.reviews import get_review_service, tenant_dependency
from app.api.v1.router import api_router
from app.models.review import Review
from app.models.user import User
from app.services.review_service import (
    ReviewAlreadyExistsError,
    ReviewContactRequestNotFoundError,
    ReviewEligibilityError,
)


class ReviewEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.tenant = User(user_id=6)
        self.app.dependency_overrides[get_review_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[tenant_dependency] = lambda: self.tenant
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_review() -> Review:
        return Review(
            review_id=3,
            contact_request_id=9,
            rating=5,
            comment="Great experience.",
            created_at=datetime(2026, 11, 2, 9, 0),
        )

    def test_create_review_uses_authenticated_tenant(self) -> None:
        self.service.create_for_tenant.return_value = self.make_review()

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={
                "contact_request_id": 9,
                "rating": 5,
                "comment": "Great experience.",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["review_id"], 3)
        self.assertNotIn("tenant_id", response.json())
        self.service.create_for_tenant.assert_called_once()
        self.assertEqual(
            self.service.create_for_tenant.call_args.args[0],
            self.tenant.user_id,
        )

    def test_list_reviews_uses_authenticated_tenant(self) -> None:
        self.service.list_for_tenant.return_value = [self.make_review()]

        response = self.client.get("/api/v1/users/me/reviews")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["contact_request_id"], 9)
        self.service.list_for_tenant.assert_called_once_with(
            self.tenant.user_id,
        )

    def test_list_reviews_handles_database_error(self) -> None:
        self.service.list_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        response = self.client.get("/api/v1/users/me/reviews")

        self.assertEqual(response.status_code, 503)

    def test_create_review_validates_rating(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 6},
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_for_tenant.assert_not_called()

    def test_create_review_requires_positive_request_id(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 0, "rating": 5},
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_for_tenant.assert_not_called()

    def test_create_review_maps_ineligible_request_to_conflict(self) -> None:
        self.service.create_for_tenant.side_effect = ReviewEligibilityError(
            "Only approved contact requests can be reviewed.",
        )

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 5},
        )

        self.assertEqual(response.status_code, 409)

    def test_create_review_maps_missing_owned_request_to_not_found(self) -> None:
        self.service.create_for_tenant.side_effect = (
            ReviewContactRequestNotFoundError("Contact request not found.")
        )

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 5},
        )

        self.assertEqual(response.status_code, 404)

    def test_create_review_maps_duplicate_to_conflict(self) -> None:
        self.service.create_for_tenant.side_effect = ReviewAlreadyExistsError(
            "A review already exists.",
        )

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 5},
        )

        self.assertEqual(response.status_code, 409)

    def test_create_review_maps_database_failure_to_service_unavailable(
        self,
    ) -> None:
        self.service.create_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 5},
        )

        self.assertEqual(response.status_code, 503)

    def test_review_route_requires_tenant_role(self) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)

        response = self.client.post(
            "/api/v1/users/me/reviews",
            json={"contact_request_id": 9, "rating": 5},
        )

        self.assertEqual(response.status_code, 401)
        self.service.create_for_tenant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
