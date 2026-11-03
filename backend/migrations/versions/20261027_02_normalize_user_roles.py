"""Normalize user roles into roles and user_roles tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261027_02"
down_revision = "20261027_01"
branch_labels = None
depends_on = None


ROLE_NAMES = ("tenant", "landlord", "admin")


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column(
            "role_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("role_id", name="roles_pkey"),
        sa.UniqueConstraint("name", name="roles_name_key"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="user_roles_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.role_id"],
            name="user_roles_role_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            "role_id",
            name="user_roles_pkey",
        ),
    )

    roles_table = sa.table(
        "roles",
        sa.column("role_id", sa.BigInteger()),
        sa.column("name", sa.String(length=50)),
    )
    op.bulk_insert(
        roles_table,
        [{"name": role_name} for role_name in ROLE_NAMES],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT users.user_id, roles.role_id
            FROM users
            JOIN roles ON roles.name = users.role::text
            """
        )
    )

    connection = op.get_bind()
    unmapped_users = connection.execute(
        sa.text(
            """
            SELECT count(*)
            FROM users
            LEFT JOIN user_roles ON user_roles.user_id = users.user_id
            WHERE user_roles.user_id IS NULL
            """
        )
    ).scalar_one()
    if unmapped_users:
        raise RuntimeError(
            "Cannot migrate users with roles missing from the roles table."
        )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role_enum")


def downgrade() -> None:
    connection = op.get_bind()
    invalid_role_assignments = connection.execute(
        sa.text(
            """
            SELECT count(*)
            FROM users
            LEFT JOIN (
                SELECT user_id, count(*) AS role_count
                FROM user_roles
                GROUP BY user_id
            ) assignments ON assignments.user_id = users.user_id
            WHERE coalesce(assignments.role_count, 0) <> 1
               OR EXISTS (
                    SELECT 1
                    FROM user_roles
                    JOIN roles USING (role_id)
                    WHERE user_roles.user_id = users.user_id
                      AND roles.name NOT IN ('tenant', 'landlord', 'admin')
               )
            """
        )
    ).scalar_one()
    if invalid_role_assignments:
        raise RuntimeError(
            "Cannot downgrade users with missing, multiple, or unsupported roles."
        )

    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('landlord', 'tenant', 'admin')"
    )
    role_enum = postgresql.ENUM(
        *ROLE_NAMES,
        name="user_role_enum",
        create_type=False,
    )
    op.add_column(
        "users",
        sa.Column("role", role_enum, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role = roles.name::user_role_enum
            FROM user_roles
            JOIN roles USING (role_id)
            WHERE user_roles.user_id = users.user_id
            """
        )
    )
    op.alter_column(
        "users",
        "role",
        existing_type=role_enum,
        nullable=False,
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        nullable=True,
    )
    op.drop_table("user_roles")
    op.drop_table("roles")
