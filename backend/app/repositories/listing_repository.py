from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, func
from sqlalchemy.orm import Session

from app.models.listing import Listing


_listing_moderation = Table(
    "listing_moderation",
    MetaData(),
    Column("moderation_id", BigInteger),
    Column("listing_id", BigInteger),
    Column("decision", String(8)),
    Column("decided_at", DateTime),
)


class ListingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Listing]:
        statement = select(Listing).order_by(
            Listing.created_at.desc(),
            Listing.listing_id.desc(),
        )
        return list(self._db.scalars(statement).all())

    def get_by_id(self, listing_id: int) -> Listing | None:
        return self._db.get(Listing, listing_id)

    def get_latest_moderation_decisions(
        self,
        listing_ids: Sequence[int],
    ) -> dict[int, str]:
        if not listing_ids:
            return {}

        ranked_decisions = (
            select(
                _listing_moderation.c.listing_id,
                _listing_moderation.c.decision,
                func.row_number()
                .over(
                    partition_by=_listing_moderation.c.listing_id,
                    order_by=(
                        _listing_moderation.c.decided_at.desc(),
                        _listing_moderation.c.moderation_id.desc(),
                    ),
                )
                .label("decision_rank"),
            )
            .where(_listing_moderation.c.listing_id.in_(listing_ids))
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
