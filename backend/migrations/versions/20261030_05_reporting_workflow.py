"""Extend the report table for the Phase 7 reporting workflow."""

from alembic import op


revision = "20261030_05"
down_revision = "20261030_04"
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
                WHERE typname = 'report_reason_enum'
                  AND typnamespace = current_schema()::regnamespace
            ) THEN
                CREATE TYPE report_reason_enum AS ENUM (
                    'scam',
                    'fake_listing',
                    'inaccurate_info',
                    'abusive',
                    'other'
                );
            END IF;
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'report_status_enum'
                  AND typnamespace = current_schema()::regnamespace
            ) THEN
                CREATE TYPE report_status_enum AS ENUM (
                    'open',
                    'under_review',
                    'resolved',
                    'dismissed'
                );
            END IF;
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'report_action_enum'
                  AND typnamespace = current_schema()::regnamespace
            ) THEN
                CREATE TYPE report_action_enum AS ENUM (
                    'submitted',
                    'assigned',
                    'resolved',
                    'dismissed'
                );
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS report (
            report_id BIGINT GENERATED ALWAYS AS IDENTITY,
            listing_id BIGINT,
            target_user_id BIGINT,
            tenant_id BIGINT NOT NULL,
            admin_id BIGINT,
            reason report_reason_enum NOT NULL,
            status report_status_enum NOT NULL DEFAULT 'open',
            details TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT report_pkey PRIMARY KEY (report_id),
            CONSTRAINT report_listing_id_fkey
                FOREIGN KEY (listing_id) REFERENCES listings (listing_id),
            CONSTRAINT report_target_user_id_fkey
                FOREIGN KEY (target_user_id) REFERENCES users (user_id),
            CONSTRAINT report_tenant_id_fkey
                FOREIGN KEY (tenant_id) REFERENCES users (user_id),
            CONSTRAINT report_admin_id_fkey
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
                ON DELETE SET NULL,
            CONSTRAINT report_target_check
                CHECK (listing_id IS NOT NULL OR target_user_id IS NOT NULL)
        )
        """
    )
    op.execute("ALTER TABLE report ALTER COLUMN listing_id DROP NOT NULL")
    op.execute(
        "ALTER TABLE report ADD COLUMN IF NOT EXISTS target_user_id BIGINT",
    )
    op.execute("ALTER TABLE report ADD COLUMN IF NOT EXISTS details TEXT")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'report_target_user_id_fkey'
                  AND conrelid = 'report'::regclass
            ) THEN
                ALTER TABLE report
                    ADD CONSTRAINT report_target_user_id_fkey
                    FOREIGN KEY (target_user_id) REFERENCES users (user_id);
            END IF;
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'report_target_check'
                  AND conrelid = 'report'::regclass
            ) THEN
                ALTER TABLE report
                    ADD CONSTRAINT report_target_check
                    CHECK (
                        listing_id IS NOT NULL
                        OR target_user_id IS NOT NULL
                    ) NOT VALID;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        "ALTER TABLE report VALIDATE CONSTRAINT report_target_check",
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS report_history (
            history_id BIGINT GENERATED ALWAYS AS IDENTITY,
            report_id BIGINT NOT NULL,
            actor_user_id BIGINT NOT NULL,
            action report_action_enum NOT NULL,
            note TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT report_history_pkey PRIMARY KEY (history_id),
            CONSTRAINT report_history_report_id_fkey
                FOREIGN KEY (report_id) REFERENCES report (report_id)
                ON DELETE CASCADE,
            CONSTRAINT report_history_actor_user_id_fkey
                FOREIGN KEY (actor_user_id) REFERENCES users (user_id)
        )
        """
    )


def downgrade() -> None:
    pass
