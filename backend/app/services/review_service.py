from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.review import Review
from app.repositories.review_repository import ReviewRepository
from app.schemas.review import ReviewCreateRequest


class ReviewContactRequestNotFoundError(Exception):
    pass


class ReviewEligibilityError(Exception):
    pass


class ReviewAlreadyExistsError(Exception):
    pass


class ReviewService:
    APPROVED_CONTACT_REQUEST_STATUS = "approved"
    UNIQUE_CONTACT_REQUEST_CONSTRAINT = "reviews_contact_request_id_key"

    def __init__(self, db: Session) -> None:
        self._db = db
        self._reviews = ReviewRepository(db)

    def create_for_tenant(
        self,
        tenant_id: int,
        request: ReviewCreateRequest,
    ) -> Review:
        contact_request = self._reviews.get_contact_request_for_tenant(
            request.contact_request_id,
            tenant_id,
        )
        if contact_request is None:
            raise ReviewContactRequestNotFoundError(
                "Contact request not found.",
            )
        if contact_request.status != self.APPROVED_CONTACT_REQUEST_STATUS:
            raise ReviewEligibilityError(
                "Only approved contact requests can be reviewed.",
            )
        if (
            self._reviews.get_for_contact_request(request.contact_request_id)
            is not None
        ):
            raise ReviewAlreadyExistsError(
                "A review has already been submitted for this contact request.",
            )

        review = Review(
            contact_request_id=request.contact_request_id,
            rating=request.rating,
            comment=request.comment,
        )
        try:
            self._reviews.add(review)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == self.UNIQUE_CONTACT_REQUEST_CONSTRAINT:
                raise ReviewAlreadyExistsError(
                    "A review has already been submitted for this contact request.",
                ) from exc
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return review

    def list_for_tenant(self, tenant_id: int) -> list[Review]:
        return self._reviews.list_for_tenant(tenant_id)
