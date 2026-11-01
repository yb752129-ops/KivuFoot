"""Allow configured extra-time periods on matches and events.

Revision ID: 0030_prolongation_periods
Revises: 0029_match_qualification_slots
"""
from alembic import op

revision = "0030_prolongation_periods"
down_revision = "0029_match_qualification_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_matchs_periode", "matchs", type_="check")
    op.create_check_constraint(
        "ck_matchs_periode",
        "matchs",
        "periode IN ('1', 'mi_temps', '2', '3', 'mi_temps_et', '4') OR periode IS NULL",
    )
    op.drop_constraint("ck_evenement_periode", "evenements_match", type_="check")
    op.create_check_constraint(
        "ck_evenement_periode",
        "evenements_match",
        "periode IN ('1', '2', '3', '4') OR periode IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_evenement_periode", "evenements_match", type_="check")
    op.create_check_constraint(
        "ck_evenement_periode",
        "evenements_match",
        "periode IN ('1', '2') OR periode IS NULL",
    )
    op.drop_constraint("ck_matchs_periode", "matchs", type_="check")
    op.create_check_constraint(
        "ck_matchs_periode",
        "matchs",
        "periode IN ('1', 'mi_temps', '2') OR periode IS NULL",
    )
