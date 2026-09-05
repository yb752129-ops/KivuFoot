"""Rôle coach : composition, pas effectif, pas capture.

Revision ID: 0006_coach
Revises: 0005_refus_arbitral
"""

from alembic import op

revision = "0006_coach"
down_revision = "0005_refus_arbitral"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('collecteur','organisateur','club_manager','coach','admin','supporter')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('collecteur','organisateur','club_manager','admin','supporter')",
    )
