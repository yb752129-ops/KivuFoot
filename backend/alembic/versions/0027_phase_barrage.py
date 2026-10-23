"""Allow scheduled barrage matches before their kickoff is confirmed.

Revision ID: 0027_phase_barrage
Revises: 0026_statut_equipe_edition

Only the phase constraint and kickoff nullability change. Existing match rows
remain untouched; API validation keeps kickoff mandatory outside barrages.
"""

from alembic import op
import sqlalchemy as sa

revision = "0027_phase_barrage"
down_revision = "0026_statut_equipe_edition"
branch_labels = None
depends_on = None

OLD_PHASES = "'poule','quart','demi','finale'"
NEW_PHASES = "'poule','barrage','quart','demi','finale'"


def upgrade() -> None:
    op.drop_constraint("ck_matchs_phase", "matchs", type_="check")
    op.create_check_constraint(
        "ck_matchs_phase",
        "matchs",
        f"phase IN ({NEW_PHASES})",
    )
    op.alter_column(
        "matchs",
        "date_heure",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    non_dates = bind.execute(sa.text("SELECT COUNT(*) FROM matchs WHERE date_heure IS NULL")).scalar_one()
    barrages = bind.execute(sa.text("SELECT COUNT(*) FROM matchs WHERE phase = 'barrage'")).scalar_one()
    if non_dates or barrages:
        raise RuntimeError(
            "Cannot remove barrage support while undated or barrage matches exist. "
            "No match data has been changed."
        )
    op.alter_column(
        "matchs",
        "date_heure",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_constraint("ck_matchs_phase", "matchs", type_="check")
    op.create_check_constraint(
        "ck_matchs_phase",
        "matchs",
        f"phase IN ({OLD_PHASES})",
    )
