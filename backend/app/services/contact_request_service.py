from typing import Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.contact_request import ContactRequest
from app.repositories.contact_request_repository import (
    ContactRequestRepository,
)
from app.repositories.listing_repository import ListingRepository
from app.services.listing_service import ListingService


ContactRequestDecision = Literal["approved", "rejected", "cancelled"]


class ContactRequestListingUnavailableError(Exception):
    pass


class ContactRequestNotFoundError(Exception):
    pass


class ContactRequestForbiddenError(Exception):
    pass


class ContactRequestStateError(Exception):
    pass


class ContactRequestService:
    PENDING_STATUS = "pending"
    LANDLORD_DECISIONS = {"approved", "rejected"}
    TENANT_DECISIONS = {"cancelled"}

    def __init__(self, db: Session) -> None:
        self._db = db
        self._requests = ContactRequestRepository(db)
        self._listings = ListingRepository(db)

    def create_request(
        self,
        tenant_id: int,
        listing_id: int,
    ) -> ContactRequest:
        public_listing = ListingService(self._listings).get_public_listing(
            listing_id
        )
        if public_listing is None:
            raise ContactRequestListingUnavailableError(
                "Listing is not available for contact requests."
            )

        contact_request = ContactRequest(
            listing_id=listing_id,
            tenant_id=tenant_id,
            status=self.PENDING_STATUS,
        )
        try:
            self._requests.add(contact_request)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return contact_request

    def list_for_tenant(self, tenant_id: int) -> list[ContactRequest]:
        return self._requests.list_for_tenant(tenant_id)

    def list_for_landlord(self, landlord_id: int) -> list[ContactRequest]:
        return self._requests.list_for_landlord(landlord_id)

    def update_status(
        self,
        actor_id: int,
        request_id: int,
        new_status: ContactRequestDecision,
    ) -> ContactRequest:
        request_and_landlord = self._requests.get_with_listing_landlord(
            request_id
        )
        if request_and_landlord is None:
            raise ContactRequestNotFoundError("Contact request does not exist.")

        contact_request, landlord_id = request_and_landlord
        if contact_request.status != self.PENDING_STATUS:
            raise ContactRequestStateError(
                "Only pending contact requests can be updated."
            )

        if new_status in self.LANDLORD_DECISIONS:
            if landlord_id != actor_id or contact_request.tenant_id == actor_id:
                raise ContactRequestForbiddenError(
                    "Only the listing's landlord can respond to this request."
                )
        elif new_status in self.TENANT_DECISIONS:
            if contact_request.tenant_id != actor_id:
                raise ContactRequestForbiddenError(
                    "Only the requesting tenant can cancel this request."
                )
        else:
            raise ContactRequestStateError(
                "The requested contact-request status is not permitted."
            )

        contact_request.status = new_status
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return contact_request
