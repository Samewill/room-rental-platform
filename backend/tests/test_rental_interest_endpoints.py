import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.rental_interests import (
    get_rental_interest_service,
    landlord_dependency,
    tenant_dependency,
)
from app.api.v1.router import api_router
from app.models.user import User
from app.schemas.rental_interest import (
    InterestOpportunityResponse,
    InterestOpportunitySummary,
    RentalInterestLandlordResponse,
    RentalInterestTenantResponse,
)
from app.services.rental_interest_service import (
    RentalInterestCapacityFullError,
    RentalInterestWaitlistConsentRequiredError,
)


class RentalInterestEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.service = Mock()
        self.tenant = User(user_id=6)
        self.landlord = User(user_id=8)
        self.user = self.tenant
        self.app.dependency_overrides[get_rental_interest_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[tenant_dependency] = lambda: self.tenant
        self.app.dependency_overrides[landlord_dependency] = (
            lambda: self.landlord
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def make_tenant_response() -> RentalInterestTenantResponse:
        return RentalInterestTenantResponse(
            interest_id=42,
            opportunity=InterestOpportunitySummary(
                opportunity_id=31,
                listing_id=14,
                listing_title="Quiet single room",
                address="Main Road",
                area_name="Central",
                room_type="single_room",
                monthly_rent=Decimal("4500.00"),
                amenities=[],
                available_from=date(2027, 1, 1),
                available_until=date(2027, 3, 31),
                available_units=1,
                expected_rental_duration_months=None,
            ),
            expected_move_in_date=date(2027, 1, 15),
            expected_duration_months=12,
            monthly_budget=Decimal("5000.00"),
            preferred_room_type="single_room",
            required_amenities=[],
            status="active",
            registered_at=datetime(2026, 11, 11, 12, 0),
            expires_at=datetime(2027, 2, 9, 12, 0),
            history=[],
        )

    def test_create_interest_uses_authenticated_tenant_identity(self) -> None:
        self.service.create_interest.return_value = self.make_tenant_response()

        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
                "preferred_room_type": "single_room",
                "required_amenities": [],
            },
        )

        self.assertEqual(response.status_code, 201)
        self.service.create_interest.assert_called_once()
        self.assertEqual(
            self.service.create_interest.call_args.args[0:2],
            (6, 31),
        )
        self.assertEqual(response.json()["status"], "active")
        self.assertFalse(response.json()["reservation_confirmed"])

    def test_waitlist_consent_is_passed_to_the_registration_service(self) -> None:
        self.service.create_interest.return_value = self.make_tenant_response()

        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
                "join_waitlist": True,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            self.service.create_interest.call_args.args[2].join_waitlist,
        )

    def test_client_cannot_supply_tenant_identity(self) -> None:
        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "tenant_id": 8,
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_interest.assert_not_called()

    def test_client_cannot_supply_registration_status(self) -> None:
        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "status": "active",
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.service.create_interest.assert_not_called()

    def test_full_opportunity_requires_explicit_waitlist_consent(self) -> None:
        self.service.create_interest.side_effect = (
            RentalInterestWaitlistConsentRequiredError(
                "Explicit confirmation is required to join the waiting list.",
            )
        )

        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "waitlist_consent_required",
        )

    def test_full_opportunity_rejects_when_waitlist_is_disabled(self) -> None:
        self.service.create_interest.side_effect = RentalInterestCapacityFullError(
            "This opportunity is full and is not accepting waitlist registrations.",
        )

        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
                "join_waitlist": True,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "capacity_full")

    def test_renewal_accepts_waitlist_consent_payload(self) -> None:
        self.service.renew_interest.return_value = self.make_tenant_response()

        response = self.client.post(
            "/api/v1/rental-interests/42/renew",
            json={"join_waitlist": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.service.renew_interest.call_args.kwargs["join_waitlist"],
        )

    def test_public_opportunities_expose_capacity_and_waitlist_counts(self) -> None:
        self.service.list_public_opportunities.return_value = [
            InterestOpportunityResponse(
                opportunity_id=31,
                listing_id=14,
                listing_title="Quiet single room",
                address="Main Road",
                area_name="Central",
                room_type="single_room",
                monthly_rent=Decimal("4500.00"),
                amenities=[],
                available_from=date(2027, 1, 1),
                available_until=date(2027, 3, 31),
                available_units=1,
                expected_rental_duration_months=None,
                status="open",
                availability_status="full",
                max_active_registrations=5,
                active_registration_count=5,
                waitlist_count=2,
                waitlist_enabled=True,
            ),
        ]

        response = self.client.get("/api/v1/interest-opportunities")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["active_registration_count"], 5)
        self.assertEqual(response.json()[0]["max_active_registrations"], 5)
        self.assertEqual(response.json()[0]["waitlist_count"], 2)
        self.assertEqual(response.json()[0]["availability_status"], "full")
        self.assertTrue(response.json()[0]["waitlist_enabled"])

    def test_landlord_response_contains_no_private_phone_fields(self) -> None:
        tenant_response = self.make_tenant_response()
        self.service.list_for_landlord_interests.return_value = [
            RentalInterestLandlordResponse(
                **tenant_response.model_dump(),
                tenant_name="Tenant One",
                compatibility_score=2,
                compatibility_reasons=["Monthly budget covers the listing rent."],
            ),
        ]
        self.user = self.landlord

        response = self.client.get(
            "/api/v1/users/me/received-rental-interests",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()[0]
        self.assertEqual(payload["tenant_name"], "Tenant One")
        self.assertNotIn("phone_no", payload)
        self.assertNotIn("email", payload)

    def test_interest_registration_requires_tenant_role(self) -> None:
        self.app.dependency_overrides.pop(tenant_dependency)
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.post(
            "/api/v1/interest-opportunities/31/interests",
            json={
                "expected_move_in_date": "2027-01-15",
                "expected_duration_months": 12,
                "monthly_budget": 5000,
            },
        )

        self.assertEqual(response.status_code, 401)
        self.service.create_interest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
