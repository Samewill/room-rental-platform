import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import httpx

from app.core.config import Settings
from app.schemas.amenity import AmenityResponse
from app.schemas.area import AreaResponse
from app.schemas.listing import ListingResponse
from app.services.assistant_graph import (
    AssistantProviderError,
    LandlordTurn,
    TenantCriteria,
    TenantTurn,
    build_assistant_graph,
    complete_json,
)


class FakeListingService:
    def __init__(self, listings: list[ListingResponse]) -> None:
        self.listings = listings

    def list_public_listings(self) -> list[ListingResponse]:
        return self.listings

    def get_public_listing(self, listing_id: int) -> ListingResponse | None:
        return next(
            (
                listing
                for listing in self.listings
                if listing.listing_id == listing_id
            ),
            None,
        )


class AssistantGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(database_url="sqlite://")
        self.areas = [
            AreaResponse(area_id=1, name="Glenwood"),
            AreaResponse(area_id=2, name="Umbilo"),
        ]
        self.amenities = [
            AmenityResponse(amenity_id=1, name="Wi-Fi"),
            AmenityResponse(amenity_id=2, name="Parking"),
        ]
        self.listings = [
            ListingResponse(
                listing_id=10,
                area_id=1,
                title="Glenwood private room",
                description="A private room.",
                room_type="single_room",
                monthly_rent=Decimal("2800.00"),
                deposit_amount=Decimal("2800.00"),
                address="12 Example Road",
                date_available=date(2026, 12, 1),
                status="active",
                created_at=datetime(2026, 10, 1),
                amenity_names=["Wi-Fi"],
                photos=[],
            ),
            ListingResponse(
                listing_id=11,
                area_id=2,
                title="Umbilo shared room",
                description="A shared room.",
                room_type="shared_room",
                monthly_rent=Decimal("2500.00"),
                deposit_amount=Decimal("2500.00"),
                address="5 Sample Street",
                date_available=date(2026, 12, 1),
                status="active",
                created_at=datetime(2026, 10, 1),
                amenity_names=["Wi-Fi", "Parking"],
                photos=[],
            ),
        ]
        self.listing_service = FakeListingService(self.listings)

    def build_graph(self):
        return build_assistant_graph(
            self.settings,
            self.listing_service,
            self.areas,
            self.amenities,
        )

    def test_tenant_search_returns_only_service_listings_matching_filters(
        self,
    ) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=TenantTurn(
                intent="search",
                criteria=TenantCriteria(
                    location="Glenwood",
                    room_type="single_room",
                    maximum_rent=Decimal("3000"),
                    amenities=["Wi-Fi"],
                ),
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "tenant",
                    "message": "A private room in Glenwood below R3,000 with Wi-Fi",
                    "history": [],
                    "workflow_state": {},
                },
            )

        self.assertEqual(
            [item["listing"]["listing_id"] for item in result["listings"]],
            [10],
        )
        self.assertEqual(result["listings"][0]["area_name"], "Glenwood")
        self.assertIn("1 verified room", result["response"])

    def test_listing_question_uses_published_listing_service_data(self) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=TenantTurn(
                intent="listing_question",
                listing_id=10,
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "tenant",
                    "message": "What is the rent for listing 10?",
                    "history": [],
                    "workflow_state": {},
                },
            )

        self.assertEqual(len(result["listings"]), 1)
        self.assertEqual(result["listings"][0]["listing"]["monthly_rent"], "2800.00")

    def test_unsupported_amenity_does_not_return_nonmatching_rooms(self) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=TenantTurn(
                intent="search",
                criteria=TenantCriteria(
                    location="Glenwood",
                    amenities=["Air conditioning"],
                ),
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "tenant",
                    "message": "I need air conditioning",
                    "history": [],
                    "workflow_state": {},
                },
            )

        self.assertEqual(result["listings"], [])
        self.assertIn("does not currently list", result["response"])

    def test_tenant_can_remove_persisted_search_filters(self) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=TenantTurn(
                intent="search",
                clear_criteria=["maximum_rent", "amenities"],
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "tenant",
                    "message": "Remove the budget and Wi-Fi requirement.",
                    "history": [],
                    "workflow_state": {
                        "criteria": {
                            "location": "Glenwood",
                            "room_type": None,
                            "minimum_rent": None,
                            "maximum_rent": "3000",
                            "amenities": ["Wi-Fi"],
                            "available_by": None,
                        },
                    },
                },
            )

        self.assertIsNone(
            result["workflow_state"]["criteria"]["maximum_rent"],
        )
        self.assertEqual(result["workflow_state"]["criteria"]["amenities"], [])
        self.assertEqual(
            [item["listing"]["listing_id"] for item in result["listings"]],
            [10],
        )

    def test_landlord_workflow_generates_confirmable_validated_draft(
        self,
    ) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=LandlordTurn(
                area_name="Glenwood",
                title="Private room in Glenwood",
                description="A furnished private room near local transport.",
                room_type="single_room",
                monthly_rent=Decimal("2800"),
                deposit_amount=Decimal("1000"),
                address="12 Example Road",
                date_available=date(2026, 12, 1),
                amenities=["Wi-Fi"],
                amenities_answered=True,
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "landlord",
                    "message": "The details are ...",
                    "history": [],
                    "workflow_state": {},
                },
            )

        self.assertTrue(result["draft"]["ready_to_confirm"])
        self.assertEqual(result["draft"]["area_id"], 1)
        self.assertEqual(result["draft"]["amenities"], ["Wi-Fi"])
        self.assertIn("confirm", result["response"])

    def test_landlord_workflow_asks_for_missing_area_from_real_catalog(
        self,
    ) -> None:
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=LandlordTurn(
                monthly_rent=Decimal("3000"),
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "landlord",
                    "message": "The rent is R3,000.",
                    "history": [],
                    "workflow_state": {},
                },
            )

        self.assertFalse(result["draft"]["ready_to_confirm"])
        self.assertIn("Glenwood", result["response"])
        self.assertIn("Umbilo", result["response"])

    def test_unsupported_landlord_amenity_requires_a_valid_choice(self) -> None:
        existing_draft = {
            "area_id": 1,
            "area_name": "Glenwood",
            "title": "Private room",
            "description": "A private room.",
            "room_type": "single_room",
            "monthly_rent": "2800",
            "deposit_amount": "1000",
            "address": "12 Example Road",
            "date_available": "2026-12-01",
            "amenities": [],
        }
        with patch(
            "app.services.assistant_graph.complete_json",
            return_value=LandlordTurn(
                amenities=["Gym"],
                amenities_answered=True,
            ),
        ):
            result = self.build_graph().invoke(
                {
                    "role": "landlord",
                    "message": "There is a gym.",
                    "history": [],
                    "workflow_state": {
                        "draft": existing_draft,
                        "amenities_answered": False,
                    },
                },
            )

        self.assertFalse(result["draft"]["ready_to_confirm"])
        self.assertIn("does not currently list Gym", result["response"])
        self.assertEqual(result["draft"]["amenities"], [])

    def test_inception_retries_then_falls_back_to_groq(self) -> None:
        settings = Settings(
            database_url="sqlite://",
            inception_api_key="inception-key",
            groq_api_key="groq-key",
            inception_max_retries=2,
            inception_backoff_base_seconds=0.1,
        )
        successful_turn = TenantTurn(intent="general")
        with (
            patch(
                "app.services.assistant_graph._call_provider",
                side_effect=[
                    httpx.ConnectError("offline"),
                    httpx.ConnectError("offline"),
                    httpx.ConnectError("offline"),
                    successful_turn,
                ],
            ) as call_provider,
            patch("app.services.assistant_graph.time.sleep"),
        ):
            result = complete_json(
                settings,
                "prompt",
                [],
                "message",
                TenantTurn,
            )

        self.assertEqual(result, successful_turn)
        self.assertEqual(
            [call.args[0] for call in call_provider.call_args_list],
            ["inception", "inception", "inception", "groq"],
        )

    def test_missing_provider_keys_are_reported(self) -> None:
        with self.assertRaises(AssistantProviderError):
            complete_json(
                self.settings,
                "prompt",
                [],
                "message",
                TenantTurn,
            )


if __name__ == "__main__":
    unittest.main()
