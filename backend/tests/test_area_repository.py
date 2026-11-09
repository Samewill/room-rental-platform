import unittest
from unittest.mock import Mock

from app.models.area import Area
from app.repositories.area_repository import AreaRepository


class AreaRepositoryTests(unittest.TestCase):
    def test_get_or_create_reuses_existing_case_insensitive_name(self) -> None:
        db = Mock()
        existing = Area(area_id=4, name="Rosebank")
        db.scalar.return_value = existing

        result = AreaRepository(db).get_or_create("rosebank")

        self.assertIs(result, existing)
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_get_or_create_persists_a_new_arbitrary_name(self) -> None:
        db = Mock()
        db.scalar.return_value = None

        result = AreaRepository(db).get_or_create("Newtown")

        self.assertEqual(result.name, "Newtown")
        db.add.assert_called_once_with(result)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
