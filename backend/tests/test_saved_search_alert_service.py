import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.amenity import Amenity
from app.models.listing import Listing
from app.models.saved_listing import ListingAlertDelivery
from app.models.saved_search import SavedSearch
from app.services.saved_search_alert_service import SavedSearchAlertService


class SavedSearchAlertServiceTests(unittest.TestCase):
    @staticmethod
    def make_search(**values: object) -> SavedSearch:
        tenant_id = values.pop("tenant_id", 6)
        values.setdefault("amenities", [])
        return SavedSearch(tenant_id=tenant_id, **values)

    @staticmethod
    def make_listing(**values: object) -> Listing:
        defaults = {
            "listing_id": 12,
            "title": "Sunny room",
            "room_type": "single_room",
            "monthly_rent": Decimal("4200.00"),
            "address": "12 Example Road, Rosebank, Johannesburg",
            "area": SimpleNamespace(name="Rosebank"),
            "amenities": [],
            "status": "active",
        }
        return Listing(**(defaults | values))

    def test_matches_location_rent_room_type_and_amenities(self) -> None:
        search = self.make_search(
            location="Rosebank, Johannesburg",
            room_type="single_room",
            minimum_rent=Decimal("3000.00"),
            maximum_rent=Decimal("5000.00"),
            amenities=[Amenity(name="wifi")],
        )
        listing = self.make_listing(amenities=[Amenity(name="wifi")])

        self.assertTrue(SavedSearchAlertService._matches(search, listing))

    def test_rejects_listing_outside_search_criteria(self) -> None:
        search = self.make_search(
            location="Rosebank",
            room_type="single_room",
            maximum_rent=Decimal("4000.00"),
        )

        self.assertFalse(
            SavedSearchAlertService._matches(search, self.make_listing()),
        )

    def test_only_active_listings_are_sent_to_matcher(self) -> None:
        service = SavedSearchAlertService.__new__(SavedSearchAlertService)
        service._db = Mock()

        service.notify_for_approved_listing(self.make_listing(status="pending"))

        service._db.scalars.assert_not_called()

    def test_sends_one_alert_for_multiple_matching_searches(self) -> None:
        search = self.make_search(
            location="Rosebank",
            alerts_enabled=True,
        )
        matching_search = self.make_search(
            tenant_id=6,
            location="Johannesburg",
            alerts_enabled=True,
        )
        contact = SimpleNamespace(
            user_id=6,
            encrypted_phone="encrypted",
        )
        db = Mock()
        db.scalars.side_effect = [
            Mock(all=Mock(return_value=[search, matching_search])),
            Mock(all=Mock(return_value=[contact])),
        ]
        db.scalar.return_value = None
        provider = Mock()
        provider.send_template.return_value = "provider-message-id"
        service = SavedSearchAlertService(db, provider)

        with (
            patch(
                "app.services.saved_search_alert_service.decrypt_phone_number",
                return_value="+27123456789",
            ),
            patch(
                "app.services.saved_search_alert_service.get_settings",
                return_value=SimpleNamespace(
                    whatsapp_room_alert_template_name="room_alert",
                ),
            ),
        ):
            service.notify_for_approved_listing(self.make_listing())

        provider.send_template.assert_called_once()
        delivery = db.add.call_args.args[0]
        self.assertIsInstance(delivery, ListingAlertDelivery)
        self.assertEqual(delivery.status, "sent")
        self.assertEqual(delivery.provider_message_id, "provider-message-id")
        self.assertEqual(db.commit.call_count, 2)

    def test_existing_delivery_prevents_duplicate_alert(self) -> None:
        search = self.make_search(
            location="Rosebank",
            alerts_enabled=True,
        )
        contact = SimpleNamespace(
            user_id=6,
            encrypted_phone="encrypted",
        )
        db = Mock()
        db.scalars.side_effect = [
            Mock(all=Mock(return_value=[search])),
            Mock(all=Mock(return_value=[contact])),
        ]
        db.scalar.return_value = ListingAlertDelivery(
            tenant_id=6,
            listing_id=12,
            status="sent",
        )
        provider = Mock()
        service = SavedSearchAlertService(db, provider)

        service.notify_for_approved_listing(self.make_listing())

        provider.send_template.assert_not_called()
        db.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
