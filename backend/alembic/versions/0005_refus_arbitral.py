"""Refus arbitral : l'événement validé reste, le score est inversé.

Revision ID: 0005_refus_arbitral
Revises: 0004_periodes

Pas de DELETE, pas de changement de type/joueur. Colonnes d'acte sur
l'événement + audit UPDATE.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_refus_arbitral"
down_revision = "0004_periodes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evenements_match",
        sa.Column("refuse", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("evenements_match", sa.Column("motif_refus", sa.String(30), nullable=True))
    op.add_column("evenements_match", sa.Column("commentaire_refus", sa.String(), nullable=True))
    op.add_column("evenements_match", sa.Column("refuse_par_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_evenement_refuse_par",
        "evenements_match",
        "users",
        ["refuse_par_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("evenements_match", sa.Column("date_refus", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_evenement_motif_refus",
        "evenements_match",
        "motif_refus IN ('hors_jeu','faute_attaquant','main','ballon_sorti','faute_gardien','autre') OR motif_refus IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_evenement_motif_refus", "evenements_match", type_="check")
    op.drop_column("evenements_match", "date_refus")
    op.drop_constraint("fk_evenement_refuse_par", "evenements_match", type_="foreignkey")
    op.drop_column("evenements_match", "refuse_par_id")
    op.drop_column("evenements_match", "commentaire_refus")
    op.drop_column("evenements_match", "motif_refus")
    op.drop_column("evenements_match", "refuse")
