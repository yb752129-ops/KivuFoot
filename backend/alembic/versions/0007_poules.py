"""Poules et phases : matchs.phase (poule/quart/demi/finale) et matchs.groupe.

Revision ID: 0007_poules
Revises: 0006_coach
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_poules"
down_revision = "0006_coach"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matchs",
        sa.Column("phase", sa.String(10), nullable=False, server_default="poule"),
    )
    op.add_column("matchs", sa.Column("groupe", sa.String(2), nullable=True))
    op.create_check_constraint(
        "ck_matchs_phase",
        "matchs",
        "phase IN ('poule','quart','demi','finale')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_matchs_phase", "matchs", type_="check")
    op.drop_column("matchs", "groupe")
    op.drop_column("matchs", "phase")
