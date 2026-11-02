import unittest
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from app.models.contact_request import ContactRequest
from app.models.review import Review
from app.schemas.review import ReviewCreateRequest
from app.services.review_service import (
    ReviewAlreadyExistsError,
    ReviewContactRequestNotFoundError,
    ReviewEligibilityError,
    ReviewService,
)


class ReviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = ReviewService(self.db)
        self.repository = Mock()
        self.service._reviews = self.repository
        self.repository.get_for_contact_request.return_value = None
        self.request = ReviewCreateRequest(
            contact_request_id=9,
            rating=5,
            comment="Great experience.",
        )

    def test_tenant_can_review_owned_approved_request(self) -> None:
        self.repository.get_contact_request_for_tenant.return_value = (
            ContactRequest(
                request_id=9,
                tenant_id=6,
                listing_id=14,
                status="approved",
            )
        )

        result = self.service.create_for_tenant(6, self.request)

        self.assertIsInstance(result, Review)
        self.assertEqual(result.contact_request_id, 9)
        self.assertEqual(result.rating, 5)
        self.assertEqual(result.comment, "Great experience.")
        self.repository.add.assert_called_once_with(result)
        self.db.commit.assert_called_once()

    def test_other_tenants_contact_request_is_not_found(self) -> None:
        self.repository.get_contact_request_for_tenant.return_value = None

        with self.assertRaises(ReviewContactRequestNotFoundError):
            self.service.create_for_tenant(6, self.request)

        self.repository.get_for_contact_request.assert_not_called()
        self.repository.add.assert_not_called()

    def test_unapproved_contact_request_cannot_be_reviewed(self) -> None:
        self.repository.get_contact_request_for_tenant.return_value = (
            ContactRequest(
                request_id=9,
                tenant_id=6,
                listing_id=14,
                status="pending",
            )
        )

        with self.assertRaises(ReviewEligibilityError):
            self.service.create_for_tenant(6, self.request)

        self.repository.add.assert_not_called()

    def test_second_review_for_contact_request_is_rejected(self) -> None:
        self.repository.get_contact_request_for_tenant.return_value = (
            ContactRequest(
                request_id=9,
                tenant_id=6,
                listing_id=14,
                status="approved",
            )
        )
        self.repository.get_for_contact_request.return_value = Review(
            review_id=4,
            contact_request_id=9,
            rating=4,
        )

        with self.assertRaises(ReviewAlreadyExistsError):
            self.service.create_for_tenant(6, self.request)

        self.repository.add.assert_not_called()

    def test_database_failure_rolls_back(self) -> None:
        self.repository.get_contact_request_for_tenant.return_value = (
            ContactRequest(
                request_id=9,
                tenant_id=6,
                listing_id=14,
                status="approved",
            )
        )
        self.repository.add.side_effect = SQLAlchemyError("database failure")

        with self.assertRaises(SQLAlchemyError):
            self.service.create_for_tenant(6, self.request)

        self.db.rollback.assert_called_once()

    def test_list_reviews_uses_authenticated_tenant(self) -> None:
        review = Review(
            review_id=3,
            contact_request_id=9,
            rating=5,
        )
        self.repository.list_for_tenant.return_value = [review]

        result = self.service.list_for_tenant(tenant_id=6)

        self.assertEqual(result, [review])
        self.repository.list_for_tenant.assert_called_once_with(6)


if __name__ == "__main__":
    unittest.main()
