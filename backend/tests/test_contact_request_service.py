import unittest
from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError

from app.models.contact_request import ContactRequest
from app.services.contact_request_service import (
    ContactRequestForbiddenError,
    ContactRequestListingUnavailableError,
    ContactRequestNotFoundError,
    ContactRequestService,
    ContactRequestStateError,
)


class ContactRequestServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = ContactRequestService(self.db)
        self.requests = Mock()
        self.service._requests = self.requests
        self.service._listings = Mock()

    def test_create_request_starts_pending_for_public_listing(self) -> None:
        with patch(
            "app.services.contact_request_service.ListingService"
        ) as listing_service:
            listing_service.return_value.get_public_listing.return_value = (
                object()
            )

            result = self.service.create_request(tenant_id=6, listing_id=14)

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.tenant_id, 6)
        self.assertEqual(result.listing_id, 14)
        self.requests.add.assert_called_once()
        self.db.commit.assert_called_once()

    def test_create_request_rejects_non_public_listing(self) -> None:
        with patch(
            "app.services.contact_request_service.ListingService"
        ) as listing_service:
            listing_service.return_value.get_public_listing.return_value = None

            with self.assertRaises(ContactRequestListingUnavailableError):
                self.service.create_request(tenant_id=6, listing_id=14)

        self.requests.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_create_request_rolls_back_database_failure(self) -> None:
        self.requests.add.side_effect = SQLAlchemyError("database failure")
        with patch(
            "app.services.contact_request_service.ListingService"
        ) as listing_service:
            listing_service.return_value.get_public_listing.return_value = (
                object()
            )

            with self.assertRaises(SQLAlchemyError):
                self.service.create_request(tenant_id=6, listing_id=14)

        self.db.rollback.assert_called_once()

    def test_list_requests_uses_tenant_id(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.list_for_tenant.return_value = [contact_request]

        result = self.service.list_for_tenant(6)

        self.assertEqual(result, [contact_request])
        self.requests.list_for_tenant.assert_called_once_with(6)

    def test_list_received_requests_uses_landlord_id(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.list_for_landlord.return_value = [contact_request]

        result = self.service.list_for_landlord(8)

        self.assertEqual(result, [contact_request])
        self.requests.list_for_landlord.assert_called_once_with(8)

    def test_landlord_can_approve_request_for_another_tenant(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        result = self.service.update_status(8, 5, "approved")

        self.assertEqual(result.status, "approved")
        self.db.commit.assert_called_once()

    def test_landlord_can_reject_request_for_another_tenant(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        result = self.service.update_status(8, 5, "rejected")

        self.assertEqual(result.status, "rejected")

    def test_tenant_can_cancel_own_pending_request(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        result = self.service.update_status(6, 5, "cancelled")

        self.assertEqual(result.status, "cancelled")

    def test_unrelated_landlord_cannot_update_request(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        with self.assertRaises(ContactRequestForbiddenError):
            self.service.update_status(9, 5, "approved")

        self.db.commit.assert_not_called()

    def test_requesting_tenant_cannot_approve_own_request(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            6,
        )

        with self.assertRaises(ContactRequestForbiddenError):
            self.service.update_status(6, 5, "approved")

        self.db.commit.assert_not_called()

    def test_another_tenant_cannot_cancel_request(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        with self.assertRaises(ContactRequestForbiddenError):
            self.service.update_status(9, 5, "cancelled")

        self.db.commit.assert_not_called()

    def test_only_pending_requests_can_be_updated(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="approved",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )

        with self.assertRaises(ContactRequestStateError):
            self.service.update_status(8, 5, "rejected")

        self.db.commit.assert_not_called()

    def test_missing_request_is_reported(self) -> None:
        self.requests.get_with_listing_landlord.return_value = None

        with self.assertRaises(ContactRequestNotFoundError):
            self.service.update_status(8, 5, "approved")

    def test_database_failure_while_updating_rolls_back(self) -> None:
        contact_request = ContactRequest(
            request_id=5,
            listing_id=14,
            tenant_id=6,
            status="pending",
        )
        self.requests.get_with_listing_landlord.return_value = (
            contact_request,
            8,
        )
        self.db.commit.side_effect = SQLAlchemyError("database failure")

        with self.assertRaises(SQLAlchemyError):
            self.service.update_status(8, 5, "approved")

        self.db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
