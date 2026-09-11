"""Numéros de maillot : profil et contexte match.

Revision ID: 0010_numero
Revises: 0009_composition

Ajouts non destructifs :
- joueurs.numero (numéro de profil, optionnel) ;
- match_participations.numero (numéro porté pour un match précis).
Le numéro ne sert JAMAIS d'identifiant (règle de la spécification).
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_numero"
down_revision = "0009_composition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("joueurs", sa.Column("numero", sa.Integer(), nullable=True))
    op.add_column("match_participations", sa.Column("numero", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("match_participations", "numero")
    op.drop_column("joueurs", "numero")
