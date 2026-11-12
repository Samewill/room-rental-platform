import unittest
from unittest.mock import Mock

from sqlalchemy.dialects import postgresql

from app.repositories.rental_interest_repository import (
    RentalInterestRepository,
)


class RentalInterestRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.db.scalars.return_value.unique.return_value.all.return_value = []
        self.repository = RentalInterestRepository(self.db)

    def test_landlord_opportunity_and_registration_queries_are_distinct(
        self,
    ) -> None:
        self.repository.list_opportunities_for_landlord(8)
        opportunity_query = str(self.db.scalars.call_args.args[0])

        self.db.scalars.reset_mock()
        self.repository.list_interests_for_landlord(8)
        interest_query = str(self.db.scalars.call_args.args[0])

        self.assertIn("rental_interest_opportunities", opportunity_query)
        self.assertNotIn("rental_interests.", opportunity_query)
        self.assertIn("rental_interests", interest_query)

    def test_capacity_lock_compiles_to_postgresql_row_lock(self) -> None:
        self.repository.get_opportunity(31, for_update=True)
        statement = self.db.scalar.call_args.args[0]

        sql = str(statement.compile(dialect=postgresql.dialect()))

        self.assertIn(
            "FOR UPDATE OF rental_interest_opportunities",
            sql,
        )


if __name__ == "__main__":
    unittest.main()
