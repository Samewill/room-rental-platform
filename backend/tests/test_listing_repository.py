import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.area import Area
from app.models.listing import Listing
from app.models.listing_moderation import ListingModeration
from app.models.user import User
from app.repositories.listing_repository import ListingRepository


class ListingRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.repository = ListingRepository(self.session)
        self._next_moderation_id = 0

        @event.listens_for(self.session, "before_flush")
        def assign_moderation_ids(
            session: Session,
            _flush_context: object,
            _instances: object,
        ) -> None:
            for item in session.new:
                if (
                    isinstance(item, ListingModeration)
                    and item.moderation_id is None
                ):
                    self._next_moderation_id += 1
                    item.moderation_id = self._next_moderation_id

        self.session.add_all(
            [
                User(
                    user_id=1,
                    full_name="Test Admin",
                    phone_no="555-0100",
                    email="admin@example.test",
                ),
                Area(area_id=1, name="Test area"),
            ],
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    @staticmethod
    def make_listing(
        listing_id: int,
        status: str,
        created_at: datetime,
    ) -> Listing:
        return Listing(
            listing_id=listing_id,
            landlord_id=1,
            area_id=1,
            title=f"Room {listing_id}",
            description="A test room.",
            room_type="single_room",
            monthly_rent=Decimal("4200.00"),
            deposit_amount=Decimal("4200.00"),
            address="Test address",
            date_available=date(2026, 11, 1),
            status=status,
            created_at=created_at,
        )

    def add_decision(
        self,
        listing_id: int,
        decision: str,
        decided_at: datetime,
        reason: str | None = None,
    ) -> ListingModeration:
        if self.session.get(Listing, listing_id) is None:
            self.session.add(
                self.make_listing(
                    listing_id,
                    "active",
                    decided_at,
                ),
            )
            self.session.flush()

        moderation = self.repository.add_moderation_decision(
            listing_id=listing_id,
            admin_id=1,
            decision=decision,
            reason=reason,
        )
        moderation.decided_at = decided_at
        self.session.commit()
        return moderation

    def test_lists_pending_listings_in_creation_order(self) -> None:
        self.session.add_all(
            [
                self.make_listing(10, "pending", datetime(2026, 10, 27, 10)),
                self.make_listing(20, "active", datetime(2026, 10, 26, 10)),
                self.make_listing(30, "pending", datetime(2026, 10, 26, 10)),
            ],
        )
        self.session.commit()

        result = self.repository.list_pending_listings()

        self.assertEqual([listing.listing_id for listing in result], [30, 10])

    def test_lists_active_listings_in_creation_order(self) -> None:
        self.session.add_all(
            [
                self.make_listing(10, "active", datetime(2026, 10, 27, 10)),
                self.make_listing(20, "pending", datetime(2026, 10, 28, 10)),
                self.make_listing(30, "active", datetime(2026, 10, 26, 10)),
            ],
        )
        self.session.commit()

        result = self.repository.list_active_listings()

        self.assertEqual([listing.listing_id for listing in result], [10, 30])

    def test_lists_full_moderation_history_newest_first(self) -> None:
        self.add_decision(
            10,
            "approved",
            datetime(2026, 10, 26, 10),
            "First review",
        )
        self.add_decision(
            10,
            "rejected",
            datetime(2026, 10, 27, 10),
            "Updated review",
        )

        result = self.repository.list_moderation_history(10)

        self.assertEqual(
            [moderation.decision for moderation in result],
            ["rejected", "approved"],
        )
        self.assertEqual(
            [moderation.reason for moderation in result],
            ["Updated review", "First review"],
        )

    def test_returns_latest_decision_for_each_requested_listing(self) -> None:
        self.add_decision(10, "approved", datetime(2026, 10, 26, 10))
        self.add_decision(10, "rejected", datetime(2026, 10, 27, 10))
        self.add_decision(20, "approved", datetime(2026, 10, 26, 11))
        self.add_decision(30, "approved", datetime(2026, 10, 28, 9))

        result = self.repository.get_latest_moderation_decisions([10, 20])

        self.assertEqual(result, {10: "rejected", 20: "approved"})

    def test_uses_moderation_id_to_break_timestamp_ties(self) -> None:
        decided_at = datetime(2026, 10, 27, 10, 0)
        first = self.add_decision(10, "approved", decided_at)
        second = self.add_decision(10, "rejected", decided_at)

        result = self.repository.get_latest_moderation_decisions([10])

        self.assertGreater(second.moderation_id, first.moderation_id)
        self.assertEqual(result, {10: "rejected"})

    def test_returns_empty_mapping_for_no_requested_listings(self) -> None:
        result = self.repository.get_latest_moderation_decisions([])

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
