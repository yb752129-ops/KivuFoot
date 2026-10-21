"""Add the unified club role without changing existing users.

Revision ID: 0022_role_club
Revises: 0021_composition_positions

The application stores User.role as VARCHAR(50) protected by a PostgreSQL
CHECK constraint, not as a PostgreSQL ENUM. This migration only widens that
constraint. No users are rewritten.
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_role_club"
down_revision = "0021_composition_positions"
branch_labels = None
depends_on = None


OLD_ROLES = "'collecteur','organisateur','club_manager','coach','admin','supporter'"
NEW_ROLES = "'collecteur','organisateur','club_manager','coach','club','admin','supporter'"


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        f"role IN ({NEW_ROLES})",
    )


def downgrade() -> None:
    # A downgrade must never silently delete or rewrite accounts created with
    # role=club after this migration. Refuse until an operator has handled
    # those rows explicitly.
    bind = op.get_bind()
    club_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE role = 'club'")
    ).scalar_one()
    if club_count:
        raise RuntimeError(
            "Downgrade 0022 refused: users with role='club' still exist; "
            "no data is rewritten automatically."
        )
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        f"role IN ({OLD_ROLES})",
    )
