"""Add reversible administrative match cancellation.

Revision ID: 0025_match_annulation
Revises: 0024_role_coach_to_club

The match row and its events are deliberately retained. The extra columns
store the exact pre-cancellation state and the reason/auditable actor so an
administrator can restore the match without guessing.
"""

from alembic import op
import sqlalchemy as sa

revision = "0025_match_annulation"
down_revision = "0024_role_coach_to_club"
branch_labels = None
depends_on = None


OLD_STATUTS = "'programme','en_cours','termine','valide','conteste'"
NEW_STATUTS = "'programme','en_cours','termine','valide','conteste','annule'"


def upgrade() -> None:
    op.add_column("matchs", sa.Column("statut_avant_annulation", sa.String(20), nullable=True))
    op.add_column("matchs", sa.Column("locked_avant_annulation", sa.Boolean(), nullable=True))
    op.add_column("matchs", sa.Column("annule_motif", sa.String(500), nullable=True))
    op.add_column(
        "matchs",
        sa.Column("annule_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("matchs", sa.Column("annule_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_matchs_annule_at", "matchs", ["annule_at"])

    op.drop_constraint("ck_matchs_statut", "matchs", type_="check")
    op.create_check_constraint("ck_matchs_statut", "matchs", f"statut IN ({NEW_STATUTS})")


def downgrade() -> None:
    bind = op.get_bind()
    cancelled = bind.execute(
        sa.text("SELECT COUNT(*) FROM matchs WHERE statut = 'annule'")
    ).scalar_one()
    if cancelled:
        raise RuntimeError(
            "Downgrade 0025 refused: cancelled matches still exist; "
            "restore them through the admin action before rolling back."
        )

    op.drop_constraint("ck_matchs_statut", "matchs", type_="check")
    op.create_check_constraint("ck_matchs_statut", "matchs", f"statut IN ({OLD_STATUTS})")
    op.drop_index("ix_matchs_annule_at", table_name="matchs")
    op.drop_column("matchs", "annule_at")
    op.drop_column("matchs", "annule_par_id")
    op.drop_column("matchs", "annule_motif")
    op.drop_column("matchs", "locked_avant_annulation")
    op.drop_column("matchs", "statut_avant_annulation")
