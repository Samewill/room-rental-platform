import unittest
from datetime import datetime
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from app.models.saved_search import SavedSearch
from app.models.whatsapp import WhatsAppContact
from app.schemas.saved_search import SavedSearchCreateRequest
from app.schemas.saved_search import SavedSearchAlertsUpdateRequest
from app.services.saved_search_service import (
    SavedSearchService,
    SavedSearchWhatsAppNotEnabledError,
)


class SavedSearchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = SavedSearchService(self.db)
        self.repository = Mock()
        self.service._saved_searches = self.repository
        self.service._amenities = Mock()
        self.service._amenities.get_by_names.return_value = []

    def test_create_saved_search_uses_authenticated_tenant(self) -> None:
        request = SavedSearchCreateRequest(
            location="Rosebank",
            room_type="single_room",
            minimum_rent="1000.00",
            maximum_rent="5000.00",
        )

        result = self.service.create_for_tenant(tenant_id=6, request=request)

        self.assertIsInstance(result, SavedSearch)
        self.assertEqual(result.tenant_id, 6)
        self.assertEqual(result.location, "Rosebank")
        self.assertEqual(result.room_type, "single_room")
        self.assertEqual(result.minimum_rent, request.minimum_rent)
        self.assertEqual(result.maximum_rent, request.maximum_rent)
        self.repository.add.assert_called_once_with(result)
        self.db.commit.assert_called_once()

    def test_create_saved_search_rolls_back_database_failure(self) -> None:
        self.repository.add.side_effect = SQLAlchemyError("database failure")
        request = SavedSearchCreateRequest(location="Rosebank")

        with self.assertRaises(SQLAlchemyError):
            self.service.create_for_tenant(tenant_id=6, request=request)

        self.db.rollback.assert_called_once()

    def test_create_alert_requires_verified_whatsapp_contact(self) -> None:
        self.db.get.return_value = None
        request = SavedSearchCreateRequest(
            location="Rosebank",
            alerts_enabled=True,
        )

        with self.assertRaises(SavedSearchWhatsAppNotEnabledError):
            self.service.create_for_tenant(tenant_id=6, request=request)

        self.repository.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_create_alert_records_separate_opt_in(self) -> None:
        self.db.get.return_value = WhatsAppContact(
            user_id=6,
            verified_at=datetime(2026, 11, 5),
            opted_in_at=datetime(2026, 11, 5),
        )
        request = SavedSearchCreateRequest(
            location="Rosebank",
            alerts_enabled=True,
        )

        result = self.service.create_for_tenant(tenant_id=6, request=request)

        self.assertTrue(result.alerts_enabled)
        self.assertIsNotNone(result.alerts_opted_in_at)
        self.repository.add.assert_called_once_with(result)

    def test_enabling_alert_for_unowned_search_is_not_allowed(self) -> None:
        self.repository.get_for_tenant.return_value = None

        result = self.service.update_alerts_for_tenant(
            tenant_id=6,
            saved_search_id=4,
            request=SavedSearchAlertsUpdateRequest(alerts_enabled=True),
        )

        self.assertIsNone(result)
        self.db.get.assert_not_called()
        self.db.commit.assert_not_called()

    def test_disabling_alert_clears_its_opt_in_timestamp(self) -> None:
        saved_search = SavedSearch(
            saved_search_id=4,
            tenant_id=6,
            location="Rosebank",
            alerts_enabled=True,
            alerts_opted_in_at=datetime(2026, 11, 5),
        )
        self.repository.get_for_tenant.return_value = saved_search

        result = self.service.update_alerts_for_tenant(
            tenant_id=6,
            saved_search_id=4,
            request=SavedSearchAlertsUpdateRequest(alerts_enabled=False),
        )

        self.assertIs(result, saved_search)
        self.assertFalse(result.alerts_enabled)
        self.assertIsNone(result.alerts_opted_in_at)
        self.db.commit.assert_called_once()

    def test_list_saved_searches_uses_authenticated_tenant(self) -> None:
        saved_search = SavedSearch(
            saved_search_id=4,
            tenant_id=6,
            location="Rosebank",
        )
        self.repository.list_for_tenant.return_value = [saved_search]

        result = self.service.list_for_tenant(tenant_id=6)

        self.assertEqual(result, [saved_search])
        self.repository.list_for_tenant.assert_called_once_with(6)

    def test_delete_saved_search_commits_only_for_owned_search(self) -> None:
        self.repository.delete_for_tenant.return_value = True

        result = self.service.delete_for_tenant(tenant_id=6, saved_search_id=4)

        self.assertTrue(result)
        self.repository.delete_for_tenant.assert_called_once_with(4, 6)
        self.db.commit.assert_called_once()

    def test_delete_missing_saved_search_does_not_commit(self) -> None:
        self.repository.delete_for_tenant.return_value = False

        result = self.service.delete_for_tenant(tenant_id=6, saved_search_id=4)

        self.assertFalse(result)
        self.db.commit.assert_not_called()

    def test_delete_saved_search_rolls_back_database_failure(self) -> None:
        self.repository.delete_for_tenant.side_effect = SQLAlchemyError(
            "database failure",
        )

        with self.assertRaises(SQLAlchemyError):
            self.service.delete_for_tenant(tenant_id=6, saved_search_id=4)

        self.db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
