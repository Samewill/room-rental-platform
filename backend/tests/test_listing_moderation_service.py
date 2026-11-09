import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from app.models.listing import Listing
from app.models.listing_moderation import ListingModeration
from app.services.listing_moderation_service import (
    ListingModerationService,
    ModerationListingNotFoundError,
    ModerationReasonRequiredError,
    ModerationStateError,
)


class ListingModerationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.repository = Mock()
        self.assistant_repository = Mock()
        self.service = ListingModerationService(self.db)
        self.service._listings = self.repository
        self.service._assistant = self.assistant_repository

    @staticmethod
    def make_listing(
        *,
        listing_id: int = 12,
        status: str = "pending",
    ) -> Listing:
        return Listing(
            listing_id=listing_id,
            landlord_id=8,
            area_id=3,
            title="A room",
            description="A room description",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date(2026, 11, 1),
            status=status,
            created_at=datetime(2026, 10, 1),
        )

    def test_lists_pending_listings_as_responses(self) -> None:
        listing = self.make_listing()
        self.repository.list_pending_listings.return_value = [listing]

        result = self.service.list_pending_listings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].listing_id, 12)

    def test_lists_future_published_listings_with_approved_decisions(
        self,
    ) -> None:
        listing = self.make_listing(status="active")
        unavailable_listing = self.make_listing(
            listing_id=13,
            status="active",
        )
        unavailable_listing.date_available = date(2026, 12, 1)
        rejected_listing = self.make_listing(
            listing_id=14,
            status="active",
        )
        self.repository.list_active_listings.return_value = [
            listing,
            unavailable_listing,
            rejected_listing,
        ]
        self.repository.get_latest_moderation_decisions.return_value = {
            12: "approved",
            13: "approved",
            14: "rejected",
        }

        result = self.service.list_published_listings()

        self.assertEqual([item.listing_id for item in result], [12, 13])
        self.repository.get_latest_moderation_decisions.assert_called_once_with(
            [12, 13, 14],
        )

    def test_gets_history_for_existing_listing(self) -> None:
        listing = self.make_listing()
        history = [Mock(spec=ListingModeration)]
        self.repository.get_by_id.return_value = listing
        self.repository.list_moderation_history.return_value = history

        result = self.service.get_moderation_history(12)

        self.assertIs(result, history)
        self.repository.list_moderation_history.assert_called_once_with(12)

    def test_history_rejects_missing_listing(self) -> None:
        self.repository.get_by_id.return_value = None

        with self.assertRaises(ModerationListingNotFoundError):
            self.service.get_moderation_history(12)

        self.repository.list_moderation_history.assert_not_called()

    def test_approval_activates_pending_listing_and_records_decision(
        self,
    ) -> None:
        listing = self.make_listing()
        self.repository.get_by_id.return_value = listing

        result = self.service.approve_listing(12, 4)

        self.assertEqual(result.status, "active")
        self.repository.add_moderation_decision.assert_called_once_with(
            12,
            4,
            "approved",
            None,
        )
        self.assistant_repository.add_listing_moderation_notification.assert_called_once_with(
            8,
            12,
            "A room",
            "approved",
            None,
        )
        self.db.commit.assert_called_once()

    def test_rejection_notifies_landlord_with_reason(self) -> None:
        self.repository.get_by_id.return_value = self.make_listing()

        self.service.reject_listing(12, 4, "Missing details")

        self.assistant_repository.add_listing_moderation_notification.assert_called_once_with(
            8,
            12,
            "A room",
            "rejected",
            "Missing details",
        )

    def test_approval_trims_optional_reason(self) -> None:
        listing = self.make_listing()
        self.repository.get_by_id.return_value = listing

        self.service.approve_listing(12, 4, "  Meets requirements  ")

        self.repository.add_moderation_decision.assert_called_once_with(
            12,
            4,
            "approved",
            "Meets requirements",
        )

    def test_rejection_returns_listing_to_draft_and_records_reason(
        self,
    ) -> None:
        listing = self.make_listing()
        self.repository.get_by_id.return_value = listing

        result = self.service.reject_listing(12, 4, "  Missing details  ")

        self.assertEqual(result.status, "draft")
        self.repository.add_moderation_decision.assert_called_once_with(
            12,
            4,
            "rejected",
            "Missing details",
        )
        self.db.commit.assert_called_once()

    def test_rejection_requires_nonblank_reason(self) -> None:
        listing = self.make_listing()
        self.repository.get_by_id.return_value = listing

        with self.assertRaises(ModerationReasonRequiredError):
            self.service.reject_listing(12, 4, "  ")

        self.repository.add_moderation_decision.assert_not_called()
        self.db.commit.assert_not_called()

    def test_hiding_active_listing_marks_removed_and_flagged(self) -> None:
        listing = self.make_listing(status="active")
        self.repository.get_by_id.return_value = listing

        result = self.service.hide_listing(12, 4, "Policy violation")

        self.assertEqual(result.status, "removed")
        self.repository.add_moderation_decision.assert_called_once_with(
            12,
            4,
            "flagged",
            "Policy violation",
        )
        self.db.commit.assert_called_once()

    def test_hiding_requires_nonblank_reason(self) -> None:
        listing = self.make_listing(status="active")
        self.repository.get_by_id.return_value = listing

        with self.assertRaises(ModerationReasonRequiredError):
            self.service.hide_listing(12, 4, "")

        self.repository.add_moderation_decision.assert_not_called()
        self.db.commit.assert_not_called()

    def test_approval_rejects_non_pending_listing(self) -> None:
        self.repository.get_by_id.return_value = self.make_listing(
            status="active",
        )

        with self.assertRaises(ModerationStateError):
            self.service.approve_listing(12, 4)

        self.repository.add_moderation_decision.assert_not_called()
        self.db.commit.assert_not_called()

    def test_hiding_rejects_non_active_listing(self) -> None:
        self.repository.get_by_id.return_value = self.make_listing()

        with self.assertRaises(ModerationStateError):
            self.service.hide_listing(12, 4, "Policy violation")

        self.repository.add_moderation_decision.assert_not_called()
        self.db.commit.assert_not_called()

    def test_database_failure_rolls_back_status_and_history(self) -> None:
        listing = self.make_listing()
        self.repository.get_by_id.return_value = listing
        self.db.commit.side_effect = SQLAlchemyError("database unavailable")

        with self.assertRaises(SQLAlchemyError):
            self.service.approve_listing(12, 4)

        self.db.rollback.assert_called_once()
        self.repository.add_moderation_decision.assert_called_once()
        self.assistant_repository.add_listing_moderation_notification.assert_called_once()


if __name__ == "__main__":
    unittest.main()
