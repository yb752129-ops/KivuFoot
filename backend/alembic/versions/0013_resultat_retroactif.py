"""Résultat rétroactif et enrichissement des buteurs vérifiés.

Revision ID: 0013_resultat_retroactif
Revises: 0012_saison_club_groupes

Les colonnes ajoutées permettent de publier un score officiel saisi après
coup sans fabriquer de déroulé live. Les buteurs vérifiés ultérieurement sont
marqués comme n'ayant pas compté une seconde fois dans le score.
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_resultat_retroactif"
down_revision = "0012_saison_club_groupes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matchs",
        sa.Column("resultat_retroactif", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("matchs", sa.Column("motif_resultat_retroactif", sa.String(length=500), nullable=True))
    op.add_column("matchs", sa.Column("note_officielle", sa.Text(), nullable=True))
    op.add_column(
        "matchs",
        sa.Column("buteurs_a_verifier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "evenements_match",
        sa.Column("minute_connue", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "evenements_match",
        sa.Column("score_comptabilise", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("evenements_match", "score_comptabilise")
    op.drop_column("evenements_match", "minute_connue")
    op.drop_column("matchs", "buteurs_a_verifier")
    op.drop_column("matchs", "note_officielle")
    op.drop_column("matchs", "motif_resultat_retroactif")
    op.drop_column("matchs", "resultat_retroactif")
