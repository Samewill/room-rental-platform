import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.repositories.listing_repository import (
    ListingRepository,
    _listing_moderation,
)


class ListingRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        _listing_moderation.create(self.engine)
        self.session = Session(self.engine)
        self.repository = ListingRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def add_decision(
        self,
        moderation_id: int,
        listing_id: int,
        decision: str,
        decided_at: datetime,
    ) -> None:
        self.session.execute(
            _listing_moderation.insert().values(
                moderation_id=moderation_id,
                listing_id=listing_id,
                decision=decision,
                decided_at=decided_at,
            ),
        )

    def test_returns_latest_decision_for_each_requested_listing(self) -> None:
        self.add_decision(
            1,
            10,
            "approved",
            datetime(2026, 10, 26, 10, 0),
        )
        self.add_decision(
            2,
            10,
            "rejected",
            datetime(2026, 10, 27, 10, 0),
        )
        self.add_decision(
            3,
            20,
            "approved",
            datetime(2026, 10, 26, 11, 0),
        )
        self.add_decision(
            4,
            30,
            "approved",
            datetime(2026, 10, 28, 9, 0),
        )

        result = self.repository.get_latest_moderation_decisions([10, 20])

        self.assertEqual(result, {10: "rejected", 20: "approved"})

    def test_uses_moderation_id_to_break_timestamp_ties(self) -> None:
        decided_at = datetime(2026, 10, 27, 10, 0)
        self.add_decision(5, 10, "approved", decided_at)
        self.add_decision(6, 10, "rejected", decided_at)

        result = self.repository.get_latest_moderation_decisions([10])

        self.assertEqual(result, {10: "rejected"})

    def test_returns_empty_mapping_for_no_requested_listings(self) -> None:
        result = self.repository.get_latest_moderation_decisions([])

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
