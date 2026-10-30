from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.listing import Listing, ListingPhoto
from app.models.listing_moderation import ListingModeration


class ListingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_landlord(self, landlord_id: int) -> list[Listing]:
        statement = (
            select(Listing)
            .where(Listing.landlord_id == landlord_id)
            .order_by(Listing.created_at.desc(), Listing.listing_id.desc())
        )
        return list(self._db.scalars(statement).all())

    def get_owned(
        self,
        listing_id: int,
        landlord_id: int,
    ) -> Listing | None:
        statement = select(Listing).where(
            Listing.listing_id == listing_id,
            Listing.landlord_id == landlord_id,
        )
        return self._db.scalar(statement)

    def add(self, listing: Listing) -> Listing:
        self._db.add(listing)
        self._db.flush()
        return listing

    def add_photo(self, listing: Listing, url: str) -> None:
        listing.photos.append(ListingPhoto(url=url))

    def list_all(self) -> list[Listing]:
        statement = select(Listing).order_by(
            Listing.created_at.desc(),
            Listing.listing_id.desc(),
        )
        return list(self._db.scalars(statement).all())

    def get_by_id(self, listing_id: int) -> Listing | None:
        return self._db.get(Listing, listing_id)

    def list_pending_listings(self) -> list[Listing]:
        statement = (
            select(Listing)
            .where(Listing.status == "pending")
            .order_by(Listing.created_at, Listing.listing_id)
        )
        return list(self._db.scalars(statement).all())

    def list_active_listings(self) -> list[Listing]:
        statement = (
            select(Listing)
            .where(Listing.status == "active")
            .order_by(Listing.created_at.desc(), Listing.listing_id.desc())
        )
        return list(self._db.scalars(statement).all())

    def list_moderation_history(
        self,
        listing_id: int,
    ) -> list[ListingModeration]:
        statement = (
            select(ListingModeration)
            .where(ListingModeration.listing_id == listing_id)
            .order_by(
                ListingModeration.decided_at.desc(),
                ListingModeration.moderation_id.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def add_moderation_decision(
        self,
        listing_id: int,
        admin_id: int,
        decision: str,
        reason: str | None,
    ) -> ListingModeration:
        moderation = ListingModeration(
            listing_id=listing_id,
            admin_id=admin_id,
            decision=decision,
            reason=reason,
        )
        self._db.add(moderation)
        self._db.flush()
        return moderation

    def get_latest_moderation_decisions(
        self,
        listing_ids: Sequence[int],
    ) -> dict[int, str]:
        if not listing_ids:
            return {}

        ranked_decisions = (
            select(
                ListingModeration.listing_id,
                ListingModeration.decision,
                func.row_number()
                .over(
                    partition_by=ListingModeration.listing_id,
                    order_by=(
                        ListingModeration.decided_at.desc(),
                        ListingModeration.moderation_id.desc(),
                    ),
                )
                .label("decision_rank"),
            )
            .where(ListingModeration.listing_id.in_(listing_ids))
            .subquery()
        )
        statement = select(
            ranked_decisions.c.listing_id,
            ranked_decisions.c.decision,
        ).where(ranked_decisions.c.decision_rank == 1)

        return {
            row.listing_id: row.decision
            for row in self._db.execute(statement)
        }
