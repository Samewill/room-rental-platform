import unittest
from datetime import datetime
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.rental_interest_notifications import (
    get_rental_interest_notification_service,
    router,
)
from app.models.user import User
from app.schemas.rental_interest_notification import (
    RentalInterestNotificationResponse,
)
from app.services.rental_interest_notification_service import (
    RentalInterestNotificationNotFoundError,
)


class RentalInterestNotificationEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.service = Mock()
        self.user = User(user_id=6)
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[
            get_rental_interest_notification_service
        ] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_notification() -> RentalInterestNotificationResponse:
        return RentalInterestNotificationResponse(
            notification_id=10,
            interest_id=42,
            listing_id=14,
            event_type="interest_status_updated",
            title="Your rental interest was updated",
            body="The landlord updated your interest.",
            created_at=datetime(2026, 11, 12, 12),
            read_at=datetime(2026, 11, 12, 13),
        )

    def test_list_notifications_uses_authenticated_recipient(self) -> None:
        self.service.list_for_user.return_value = [self.make_notification()]

        response = self.client.get(
            "/api/v1/users/me/rental-interest-notifications",
        )

        self.assertEqual(response.status_code, 200)
        self.service.list_for_user.assert_called_once_with(6)
        self.assertEqual(response.json()[0]["notification_id"], 10)

    def test_mark_read_does_not_allow_access_to_another_users_notification(
        self,
    ) -> None:
        self.service.mark_read.side_effect = (
            RentalInterestNotificationNotFoundError(
                "Notification does not exist.",
            )
        )

        response = self.client.patch(
            "/api/v1/users/me/rental-interest-notifications/10/read",
        )

        self.assertEqual(response.status_code, 404)
        self.service.mark_read.assert_called_once_with(6, 10)


if __name__ == "__main__":
    unittest.main()
