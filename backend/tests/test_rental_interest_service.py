import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, Mock, call, patch

from app.models.area import Area
from app.models.listing import Listing
from app.models.rental_interest import RentalInterestOpportunity
from app.models.rental_interest_notification import (
    RentalInterestNotification,
)
from app.models.whatsapp import WhatsAppContact
from app.schemas.rental_interest import (
    InterestOpportunityRequest,
    RentalInterestCreateRequest,
)
from app.services.rental_interest_service import (
    RentalInterestCapacityFullError,
    RentalInterestDuplicateError,
    RentalInterestForbiddenError,
    RentalInterestNotFoundError,
    RentalInterestOpportunityUnavailableError,
    RentalInterestRateLimitError,
    RentalInterestService,
    RentalInterestWaitlistConsentRequiredError,
)


class RentalInterestServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.db.get.return_value = None
        self.service = RentalInterestService.__new__(RentalInterestService)
        self.service._db = self.db
        self.service._expiry_days = 90
        self.service._max_submissions_per_day = 20
        self.service._interests = Mock()
        self.service._listings = Mock()
        self.service._amenities = Mock()
        self.listing = Listing(
            listing_id=14,
            landlord_id=8,
            area=Area(area_id=1, name="Central"),
            title="Quiet single room",
            description="A room near campus.",
            room_type="single_room",
            monthly_rent=Decimal("4500.00"),
            deposit_amount=Decimal("4500.00"),
            address="Main Road",
            date_available=date(2027, 1, 1),
            status="active",
        )
        self.opportunity = RentalInterestOpportunity(
            opportunity_id=31,
            listing_id=14,
            listing=self.listing,
            status="open",
            available_from=date(2027, 1, 1),
            available_until=date(2027, 3, 31),
            max_active_registrations=1,
            waitlist_enabled=True,
        )
        self.service._listings.get_by_id.return_value = self.listing
        self.service._listings.get_latest_moderation_decisions.return_value = {
            14: "approved",
        }
        self.service._interests.get_opportunity.return_value = self.opportunity
        self.service._interests.get_duplicate.return_value = None
        self.service._interests.count_recent_submissions.return_value = 0
        self.service._interests.count_registered.return_value = 0
        self.service._amenities.get_by_names.return_value = []
        self.service._interests.add_interest.side_effect = self._assign_interest_id

    @staticmethod
    def _assign_interest_id(interest):
        interest.interest_id = 42
        return interest

    def make_request(self) -> RentalInterestCreateRequest:
        return RentalInterestCreateRequest(
            expected_move_in_date=date(2027, 1, 15),
            expected_duration_months=12,
            monthly_budget=Decimal("5000.00"),
            preferred_room_type="single_room",
        )

    def test_create_interest_uses_server_identity_and_initial_status(self) -> None:
        result = self.service.create_interest(
            tenant_id=6,
            opportunity_id=31,
            changes=self.make_request(),
        )

        self.assertEqual(result.interest_id, 42)
        self.assertEqual(result.status, "active")
        self.assertEqual(result.opportunity.opportunity_id, 31)
        self.service._interests.lock_tenant.assert_called_once_with(6)
        self.service._interests.get_opportunity.assert_called_once_with(
            31,
            for_update=True,
        )
        self.service._interests.add_interest.assert_called_once()
        self.service._interests.add_history.assert_called_once()
        self.db.add.assert_called_once()
        notification = self.db.add.call_args.args[0]
        self.assertIsInstance(notification, RentalInterestNotification)
        self.assertEqual(notification.recipient_user_id, 8)
        self.assertEqual(notification.interest_id, 42)
        self.assertEqual(notification.listing_id, 14)
        self.assertEqual(notification.event_type, "interest_registered")
        self.assertEqual(notification.whatsapp_delivery_status, "skipped")
        self.assertNotIn("+27", notification.body)
        self.db.commit.assert_called_once()
        service_calls = self.service._interests.mock_calls
        self.assertLess(
            service_calls.index(call.lock_tenant(6)),
            service_calls.index(call.get_opportunity(31, for_update=True)),
        )

    def test_public_opportunity_includes_registration_capacity(self) -> None:
        self.service._interests.list_public_opportunities.return_value = [
            self.opportunity,
        ]
        self.service._interests.count_registered.return_value = 1
        self.service._interests.count_status.return_value = 3

        opportunities = self.service.list_public_opportunities()

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].max_active_registrations, 1)
        self.assertEqual(opportunities[0].active_registration_count, 1)
        self.assertEqual(opportunities[0].waitlist_count, 3)
        self.assertEqual(opportunities[0].availability_status, "full")
        self.assertTrue(opportunities[0].waitlist_enabled)
        self.assertEqual(opportunities[0].address, "Main Road")

    def test_landlord_opportunities_use_the_opportunity_repository_query(
        self,
    ) -> None:
        self.service._interests.list_opportunities_for_landlord.return_value = [
            self.opportunity,
        ]
        self.service._interests.count_registered.return_value = 0
        self.service._interests.count_status.return_value = 0

        opportunities = self.service.list_for_landlord(8)

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].opportunity_id, 31)
        self.service._interests.list_opportunities_for_landlord.assert_called_once_with(
            8,
        )

    def test_closed_opportunity_rejects_registration(self) -> None:
        self.opportunity.status = "closed"

        with self.assertRaises(RentalInterestOpportunityUnavailableError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_full_capacity_requires_explicit_waitlist_consent(self) -> None:
        self.service._interests.count_registered.return_value = 1

        with self.assertRaises(RentalInterestWaitlistConsentRequiredError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_tenant_can_join_waitlist_after_explicit_consent(self) -> None:
        self.service._interests.count_registered.return_value = 1
        request = self.make_request().model_copy(update={"join_waitlist": True})

        result = self.service.create_interest(
            tenant_id=6,
            opportunity_id=31,
            changes=request,
        )

        self.assertEqual(result.status, "waitlisted")
        self.assertEqual(
            self.service._interests.add_history.call_args.kwargs["to_status"],
            "waitlisted",
        )

    def test_full_capacity_rejects_when_landlord_disabled_waitlist(self) -> None:
        self.opportunity.waitlist_enabled = False
        self.service._interests.count_registered.return_value = 1
        request = self.make_request().model_copy(update={"join_waitlist": True})

        with self.assertRaises(RentalInterestCapacityFullError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=request,
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_opportunity_save_persists_waitlist_and_expected_duration(self) -> None:
        self.service._listings.get_owned.return_value = self.listing
        self.service._interests.get_opportunity_for_listing.return_value = (
            self.opportunity
        )
        self.service._interests.list_interests_for_landlord.return_value = []
        self.service._interests.count_status.return_value = 0
        changes = InterestOpportunityRequest(
            available_from=date(2027, 1, 1),
            available_until=date(2027, 3, 31),
            waitlist_enabled=True,
            expected_rental_duration_months=12,
        )

        saved = self.service.save_opportunity(8, 14, changes)

        self.assertTrue(saved.waitlist_enabled)
        self.assertEqual(saved.expected_rental_duration_months, 12)

        disabled = self.service.save_opportunity(
            8,
            14,
            changes.model_copy(update={"waitlist_enabled": False}),
        )

        self.assertFalse(disabled.waitlist_enabled)

    def test_closed_opportunity_has_closed_availability_status(self) -> None:
        self.opportunity.status = "closed"
        self.service._interests.count_registered.return_value = 0
        self.service._interests.count_status.return_value = 0

        response = self.service._opportunity_response(
            self.opportunity,
            eligible=True,
        )

        self.assertEqual(response.availability_status, "closed")

    def test_opted_in_landlord_receives_redacted_notification_outbox_row(
        self,
    ) -> None:
        self.listing.title = "Quiet room +27123456789"
        now = datetime.now()
        self.db.get.return_value = WhatsAppContact(
            user_id=8,
            encrypted_phone="encrypted",
            phone_lookup_hash="lookup",
            verified_at=now,
            opted_in_at=now,
            opted_out_at=None,
        )

        self.service.create_interest(
            tenant_id=6,
            opportunity_id=31,
            changes=self.make_request(),
        )

        notification = self.db.add.call_args.args[0]
        self.assertEqual(notification.whatsapp_delivery_status, "pending")
        self.assertNotIn("+27123456789", notification.title)
        self.assertNotIn("+27123456789", notification.body)
        self.assertIn("[phone number removed]", notification.body)

    def test_duplicate_active_interest_is_rejected(self) -> None:
        self.service._interests.get_duplicate.return_value = object()

        with self.assertRaises(RentalInterestDuplicateError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_duplicate_waitlisted_interest_is_rejected(self) -> None:
        self.service._interests.get_duplicate.return_value = object()
        request = self.make_request().model_copy(update={"join_waitlist": True})

        with self.assertRaises(RentalInterestDuplicateError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=request,
            )

        self.service._interests.add_interest.assert_not_called()

    def test_capacity_is_rechecked_after_form_submission(self) -> None:
        self.service._interests.count_registered.return_value = 1
        self.service._interests.add_interest.reset_mock()

        with self.assertRaises(RentalInterestWaitlistConsentRequiredError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.get_opportunity.assert_called_once_with(
            31,
            for_update=True,
        )
        self.service._interests.add_interest.assert_not_called()

    def test_create_interest_uses_opportunity_row_lock_for_capacity(self) -> None:
        self.service.create_interest(
            tenant_id=6,
            opportunity_id=31,
            changes=self.make_request(),
        )

        calls = self.service._interests.mock_calls
        lock_call = call.get_opportunity(31, for_update=True)
        count_call = call.count_registered(31)
        add_call = call.add_interest(ANY)
        self.assertLess(calls.index(lock_call), calls.index(count_call))
        self.assertLess(calls.index(count_call), calls.index(add_call))

    def test_two_tenants_cannot_both_claim_the_final_active_slot(self) -> None:
        self.service._interests.count_registered.side_effect = [0, 1]

        first = self.service.create_interest(
            tenant_id=6,
            opportunity_id=31,
            changes=self.make_request(),
        )
        with self.assertRaises(RentalInterestWaitlistConsentRequiredError):
            self.service.create_interest(
                tenant_id=7,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.assertEqual(first.status, "active")
        self.assertEqual(self.service._interests.add_interest.call_count, 1)


    def test_tenant_cannot_register_interest_in_own_listing(self) -> None:
        with self.assertRaises(RentalInterestForbiddenError):
            self.service.create_interest(
                tenant_id=8,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_landlord_cannot_create_opportunity_for_another_landlords_listing(
        self,
    ) -> None:
        self.service._listings.get_owned.return_value = None

        with self.assertRaises(RentalInterestNotFoundError):
            self.service.save_opportunity(
                landlord_id=8,
                listing_id=14,
                changes=InterestOpportunityRequest(
                    available_from=date(2027, 1, 1),
                ),
            )

        self.service._interests.get_opportunity_for_listing.assert_not_called()
        self.db.commit.assert_not_called()

    def test_landlord_cannot_update_interest_for_another_landlords_listing(
        self,
    ) -> None:
        interest = SimpleNamespace(
            interest_id=42,
            opportunity_id=31,
            status="active",
        )
        self.service._interests.get_interest.return_value = interest
        self.listing.landlord_id = 99

        with self.assertRaises(RentalInterestForbiddenError):
            self.service.update_status(
                landlord_id=8,
                interest_id=42,
                new_status="contacted",
            )

        self.service._db.commit.assert_not_called()

    def test_daily_submission_limit_is_enforced(self) -> None:
        self.service._interests.count_recent_submissions.return_value = 20

        with self.assertRaises(RentalInterestRateLimitError):
            self.service.create_interest(
                tenant_id=6,
                opportunity_id=31,
                changes=self.make_request(),
            )

        self.service._interests.add_interest.assert_not_called()
        self.db.commit.assert_not_called()

    def test_priority_is_explainable_and_registration_time_breaks_ties(
        self,
    ) -> None:
        def candidate(
            interest_id: int,
            budget: str,
            registered_at: datetime,
            room_type: str | None,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                interest_id=interest_id,
                status="active",
                expected_move_in_date=date(2027, 1, 15),
                registered_at=registered_at,
                monthly_budget=Decimal(budget),
                preferred_room_type=room_type,
                required_amenities=[],
                opportunity=self.opportunity,
            )

        earlier = candidate(
            1,
            "5000.00",
            datetime(2026, 11, 1),
            "single_room",
        )
        later = candidate(
            2,
            "5000.00",
            datetime(2026, 11, 2),
            "single_room",
        )
        lower_compatibility = candidate(
            3,
            "3000.00",
            datetime(2026, 10, 1),
            "shared_room",
        )

        ranked = sorted(
            [later, lower_compatibility, earlier],
            key=self.service._priority_key,
        )

        self.assertEqual(
            [interest.interest_id for interest in ranked],
            [1, 2, 3],
        )
        score, reasons = self.service._compatibility(earlier)
        self.assertEqual(score, 2)
        self.assertIn("Monthly budget covers the listing rent.", reasons)

    def test_waitlist_promotion_uses_compatibility_then_registration_time(
        self,
    ) -> None:
        self.opportunity.waitlist_enabled = False

        def candidate(
            interest_id: int,
            budget: str,
            registered_at: datetime,
            room_type: str | None,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                interest_id=interest_id,
                tenant_id=6,
                status="waitlisted",
                expected_move_in_date=date(2027, 1, 15),
                registered_at=registered_at,
                expires_at=datetime(2027, 2, 1),
                monthly_budget=Decimal(budget),
                preferred_room_type=room_type,
                required_amenities=[],
                opportunity=self.opportunity,
            )

        older_mismatch = candidate(
            1,
            "3000.00",
            datetime(2026, 10, 1),
            "shared_room",
        )
        newer_match = candidate(
            2,
            "5000.00",
            datetime(2026, 11, 1),
            "single_room",
        )
        self.service._interests.count_registered.side_effect = [0, 1]
        self.service._interests.list_waitlisted.side_effect = [
            [older_mismatch, newer_match],
        ]

        self.service._promote_waitlist(self.opportunity, None)

        self.assertEqual(newer_match.status, "active")
        self.assertEqual(older_mismatch.status, "waitlisted")
        self.service._interests.add_history.assert_called_once()
        notification = self.db.add.call_args.args[0]
        self.assertEqual(notification.event_type, "interest_promoted")
        self.assertEqual(notification.recipient_user_id, 6)

    def test_withdrawal_releases_active_capacity_and_promotes_waitlist(self) -> None:
        interest = SimpleNamespace(
            interest_id=42,
            tenant_id=6,
            status="active",
            expected_move_in_date=date(2027, 1, 15),
            expected_duration_months=12,
            monthly_budget=Decimal("5000.00"),
            preferred_room_type="single_room",
            required_amenities=[],
            registered_at=datetime(2026, 11, 1),
            expires_at=datetime(2027, 1, 30),
            history=[],
            opportunity=self.opportunity,
        )
        self.service._get_interest_and_lock_opportunity = Mock(
            return_value=(interest, self.opportunity),
        )
        self.service._promote_waitlist = Mock()

        result = self.service.withdraw_interest(6, 42)

        self.assertEqual(result.status, "withdrawn")
        self.service._promote_waitlist.assert_called_once_with(
            self.opportunity,
            42,
        )
        self.service._interests.add_history.assert_called_once()
        self.db.commit.assert_called_once()

    def test_renewal_requires_consent_before_waitlisting(self) -> None:
        expired_interest = SimpleNamespace(
            interest_id=42,
            tenant_id=6,
            status="expired",
            expected_move_in_date=date(2027, 1, 15),
            expected_duration_months=12,
            monthly_budget=Decimal("5000.00"),
            preferred_room_type="single_room",
            required_amenities=[],
            registered_at=datetime(2026, 11, 1),
            expires_at=datetime(2027, 1, 30),
            history=[],
            opportunity=self.opportunity,
        )
        self.service._get_interest_and_lock_opportunity = Mock(
            return_value=(expired_interest, self.opportunity),
        )
        self.service._interests.get_duplicate.return_value = None
        self.service._interests.count_registered.return_value = 1

        with self.assertRaises(RentalInterestWaitlistConsentRequiredError):
            self.service.renew_interest(6, 42)

        self.assertEqual(expired_interest.status, "expired")
        self.db.commit.assert_not_called()

    def test_renewal_can_join_waitlist_after_consent(self) -> None:
        expired_interest = SimpleNamespace(
            interest_id=42,
            tenant_id=6,
            status="expired",
            expected_move_in_date=date(2027, 1, 15),
            expected_duration_months=12,
            monthly_budget=Decimal("5000.00"),
            preferred_room_type="single_room",
            required_amenities=[],
            registered_at=datetime(2026, 11, 1),
            expires_at=datetime(2027, 1, 30),
            history=[],
            opportunity=self.opportunity,
        )
        self.service._get_interest_and_lock_opportunity = Mock(
            return_value=(expired_interest, self.opportunity),
        )
        self.service._interests.get_duplicate.return_value = None
        self.service._interests.count_registered.return_value = 1

        result = self.service.renew_interest(6, 42, join_waitlist=True)

        self.assertEqual(result.status, "waitlisted")
        self.db.commit.assert_called_once()

    def test_expiry_job_transitions_due_interest_and_checks_waitlist(self) -> None:
        expired_interest = SimpleNamespace(
            interest_id=42,
            tenant_id=6,
            status="active",
            opportunity=self.opportunity,
        )
        self.service._interests.list_open_opportunities.return_value = []
        self.service._interests.list_due.return_value = [(31, 42)]
        self.service._interests.list_due_for_update.return_value = [
            expired_interest,
        ]
        self.service._interests.count_registered.return_value = 0
        self.service._interests.list_waitlisted.return_value = []

        expired_count = self.service.expire_due_interests(
            now=datetime(2027, 2, 1),
        )

        self.assertEqual(expired_count, 1)
        self.assertEqual(expired_interest.status, "expired")
        self.service._interests.add_history.assert_called_once()
        notification = self.db.add.call_args.args[0]
        self.assertEqual(notification.event_type, "interest_expired")
        self.assertEqual(notification.recipient_user_id, 6)
        self.db.commit.assert_called_once()

    def test_request_schemas_reject_past_move_in_dates(self) -> None:
        with self.assertRaises(ValueError):
            InterestOpportunityRequest(
                available_from=date(2000, 1, 1),
            )
        with self.assertRaises(ValueError):
            RentalInterestCreateRequest(
                expected_move_in_date=date(2000, 1, 1),
                expected_duration_months=12,
                monthly_budget=Decimal("5000.00"),
            )


if __name__ == "__main__":
    unittest.main()
