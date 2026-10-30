"""Ensure the listing moderation schema exists."""

from alembic import op


revision = "20261030_04"
down_revision = "20261029_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'moderation_decision_enum'
                  AND typnamespace = current_schema()::regnamespace
            ) THEN
                CREATE TYPE moderation_decision_enum AS ENUM (
                    'approved',
                    'rejected',
                    'flagged'
                );
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS listing_moderation (
            moderation_id BIGINT GENERATED ALWAYS AS IDENTITY,
            listing_id BIGINT NOT NULL,
            admin_id BIGINT NOT NULL,
            decision moderation_decision_enum NOT NULL,
            reason TEXT,
            decided_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT listing_moderation_pkey
                PRIMARY KEY (moderation_id),
            CONSTRAINT listing_moderation_listing_id_fkey
                FOREIGN KEY (listing_id) REFERENCES listings (listing_id),
            CONSTRAINT listing_moderation_admin_id_fkey
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
        )
        """
    )


def downgrade() -> None:
    pass
