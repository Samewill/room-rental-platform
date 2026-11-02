from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact_request import ContactRequest
from app.models.listing import Listing


class ContactRequestRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, contact_request: ContactRequest) -> ContactRequest:
        self._db.add(contact_request)
        self._db.flush()
        return contact_request

    def list_for_tenant(self, tenant_id: int) -> list[ContactRequest]:
        statement = (
            select(ContactRequest)
            .where(ContactRequest.tenant_id == tenant_id)
            .order_by(
                ContactRequest.requested_at.desc(),
                ContactRequest.request_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def list_for_landlord(self, landlord_id: int) -> list[ContactRequest]:
        statement = (
            select(ContactRequest)
            .join(Listing, Listing.listing_id == ContactRequest.listing_id)
            .where(Listing.landlord_id == landlord_id)
            .order_by(
                ContactRequest.requested_at.desc(),
                ContactRequest.request_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def get_with_listing_landlord(
        self,
        request_id: int,
    ) -> tuple[ContactRequest, int] | None:
        statement = (
            select(ContactRequest, Listing.landlord_id)
            .join(Listing, Listing.listing_id == ContactRequest.listing_id)
            .where(ContactRequest.request_id == request_id)
        )
        result = self._db.execute(statement).one_or_none()
        if result is None:
            return None

        contact_request, landlord_id = result
        return contact_request, landlord_id
