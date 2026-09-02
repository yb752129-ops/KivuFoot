"""Périodes de match et minutes d'additionnel (Vague 2).

Revision ID: 0004_periodes
Revises: 0003_match_chrono

La mi-temps n'est PAS un StatutMatch (décision C5 inchangée).
45+2 est stocké minute + minute_additionnelle, jamais une chaîne.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_periodes"
down_revision = "0003_match_chrono"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matchs", sa.Column("periode", sa.String(12), nullable=True))
    op.add_column("matchs", sa.Column("periode_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("matchs", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_matchs_periode",
        "matchs",
        "periode IN ('1', 'mi_temps', '2') OR periode IS NULL",
    )

    op.add_column("evenements_match", sa.Column("periode", sa.String(12), nullable=True))
    op.add_column(
        "evenements_match",
        sa.Column("minute_additionnelle", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_evenement_periode",
        "evenements_match",
        "periode IN ('1', '2') OR periode IS NULL",
    )
    op.create_check_constraint(
        "ck_evenement_minute_additionnelle",
        "evenements_match",
        "minute_additionnelle >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_evenement_minute_additionnelle", "evenements_match", type_="check")
    op.drop_constraint("ck_evenement_periode", "evenements_match", type_="check")
    op.drop_column("evenements_match", "minute_additionnelle")
    op.drop_column("evenements_match", "periode")
    op.drop_constraint("ck_matchs_periode", "matchs", type_="check")
    op.drop_column("matchs", "paused_at")
    op.drop_column("matchs", "periode_started_at")
    op.drop_column("matchs", "periode")
