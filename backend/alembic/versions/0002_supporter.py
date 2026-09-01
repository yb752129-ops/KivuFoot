"""Rôle supporter pour l'inscription publique.

Revision ID: 0002_supporter
Revises: 0001_initial
"""

from alembic import op

revision = "0002_supporter"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('collecteur','organisateur','club_manager','admin','supporter')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('collecteur','organisateur','club_manager','admin')",
    )
