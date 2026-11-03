from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact_request import ContactRequest
from app.models.review import Review


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_contact_request_for_tenant(
        self,
        contact_request_id: int,
        tenant_id: int,
    ) -> ContactRequest | None:
        statement = select(ContactRequest).where(
            ContactRequest.request_id == contact_request_id,
            ContactRequest.tenant_id == tenant_id,
        )
        return self._db.scalar(statement)

    def get_for_contact_request(
        self,
        contact_request_id: int,
    ) -> Review | None:
        statement = select(Review).where(
            Review.contact_request_id == contact_request_id,
        )
        return self._db.scalar(statement)

    def list_for_tenant(self, tenant_id: int) -> list[Review]:
        statement = (
            select(Review)
            .join(
                ContactRequest,
                ContactRequest.request_id == Review.contact_request_id,
            )
            .where(ContactRequest.tenant_id == tenant_id)
            .order_by(Review.created_at.desc(), Review.review_id.desc())
        )
        return list(self._db.scalars(statement).all())

    def add(self, review: Review) -> Review:
        self._db.add(review)
        self._db.flush()
        return review
