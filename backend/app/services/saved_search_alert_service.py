import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.whatsapp_privacy import decrypt_phone_number
from app.models.listing import Listing
from app.models.saved_listing import ListingAlertDelivery
from app.models.saved_search import SavedSearch
from app.models.whatsapp import WhatsAppContact
from app.services.whatsapp_provider import (
    WhatsAppCloudAPI,
    WhatsAppProviderError,
)


logger = logging.getLogger(__name__)


class SavedSearchAlertService:
    def __init__(
        self,
        db: Session,
        provider: WhatsAppCloudAPI | None = None,
    ) -> None:
        self._db = db
        self._provider = provider or WhatsAppCloudAPI()

    def notify_for_approved_listing(self, listing: Listing) -> None:
        if listing.status != "active":
            return

        searches = list(
            self._db.scalars(
                select(SavedSearch).where(SavedSearch.alerts_enabled.is_(True)),
            ).all(),
        )
        matching_tenants = {
            search.tenant_id
            for search in searches
            if self._matches(search, listing)
        }
        if not matching_tenants:
            return

        contacts = self._db.scalars(
            select(WhatsAppContact).where(
                WhatsAppContact.user_id.in_(matching_tenants),
                WhatsAppContact.verified_at.is_not(None),
                WhatsAppContact.opted_in_at.is_not(None),
                WhatsAppContact.opted_out_at.is_(None),
            ),
        ).all()
        for contact in contacts:
            self._deliver(contact, listing)

    def _deliver(self, contact: WhatsAppContact, listing: Listing) -> None:
        existing = self._db.scalar(
            select(ListingAlertDelivery).where(
                ListingAlertDelivery.tenant_id == contact.user_id,
                ListingAlertDelivery.listing_id == listing.listing_id,
            ),
        )
        if existing is not None:
            return

        delivery = ListingAlertDelivery(
            tenant_id=contact.user_id,
            listing_id=listing.listing_id,
            status="pending",
        )
        try:
            self._db.add(delivery)
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            if self._db.scalar(
                select(ListingAlertDelivery).where(
                    ListingAlertDelivery.tenant_id == contact.user_id,
                    ListingAlertDelivery.listing_id == listing.listing_id,
                ),
            ) is not None:
                return
            raise
        except SQLAlchemyError:
            self._db.rollback()
            raise

        try:
            content = (
                f"New room matching your saved search: {listing.title} "
                f"({listing.room_type}), R{listing.monthly_rent}/month. "
                "Open Room Rentals to view it. Reply STOP to turn off "
                "WhatsApp messages."
            )
            provider_message_id = self._provider.send_template(
                decrypt_phone_number(contact.encrypted_phone),
                get_settings().whatsapp_room_alert_template_name,
                content,
            )
        except (RuntimeError, WhatsAppProviderError) as exc:
            delivery.status = "failed"
            delivery.last_error = str(exc)[:255]
            self._commit_delivery(delivery)
            logger.exception(
                "WhatsApp listing alert failed for tenant %s and listing %s",
                contact.user_id,
                listing.listing_id,
            )
            return

        delivery.status = "sent"
        delivery.provider_message_id = provider_message_id
        delivery.sent_at = self._now()
        self._commit_delivery(delivery)

    def _commit_delivery(self, delivery: ListingAlertDelivery) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    @staticmethod
    def _matches(search: SavedSearch, listing: Listing) -> bool:
        rent = Decimal(listing.monthly_rent)
        if search.minimum_rent is not None and rent < search.minimum_rent:
            return False
        if search.maximum_rent is not None and rent > search.maximum_rent:
            return False
        if search.room_type is not None and search.room_type != listing.room_type:
            return False
        if not set(search.amenity_names).issubset(listing.amenity_names):
            return False
        if search.location is None:
            return True

        location_parts = [
            part.strip().casefold()
            for part in search.location.split(",")
            if part.strip()
        ]
        return any(
            location_part in value.casefold()
            for value in (listing.address, listing.area.name)
            for location_part in location_parts
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
