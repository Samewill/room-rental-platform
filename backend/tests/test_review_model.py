import unittest

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.review import Review


class ReviewModelTests(unittest.TestCase):
    def test_table_has_expected_columns(self) -> None:
        self.assertEqual(
            set(Review.__table__.columns.keys()),
            {
                "review_id",
                "contact_request_id",
                "rating",
                "comment",
                "created_at",
            },
        )

    def test_contact_request_is_referenced_and_unique(self) -> None:
        contact_request_id = Review.__table__.c.contact_request_id
        foreign_key = next(iter(contact_request_id.foreign_keys))

        self.assertEqual(
            foreign_key.target_fullname,
            "contact_requests.request_id",
        )
        self.assertEqual(foreign_key.ondelete, "CASCADE")
        unique_constraint = next(
            constraint
            for constraint in Review.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        )
        self.assertEqual(
            [column.name for column in unique_constraint.columns],
            ["contact_request_id"],
        )

    def test_rating_is_required_and_limited_to_one_through_five(self) -> None:
        rating = Review.__table__.c.rating
        self.assertFalse(rating.nullable)

        rating_constraint = next(
            constraint
            for constraint in Review.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        )
        self.assertEqual(str(rating_constraint.sqltext), "rating BETWEEN 1 AND 5")

    def test_comment_is_optional_and_limited_to_2000_characters(self) -> None:
        comment = Review.__table__.c.comment
        self.assertTrue(comment.nullable)
        self.assertEqual(comment.type.length, 2000)


if __name__ == "__main__":
    unittest.main()
