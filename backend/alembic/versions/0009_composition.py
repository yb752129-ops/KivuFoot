"""Composition du match : formation et entraîneur par équipe.

Revision ID: 0009_composition
Revises: 0008_identite_photos

Ajouts non destructifs :
- matchs.formation_domicile / matchs.formation_exterieur (texte court, ex. 4-3-3) ;
- matchs.staff_domicile_id / matchs.staff_exterieur_id (clé vers staffs) ;
- competitions.max_remplacants (règle de la compétition, NULL = défaut plateforme).
Aucune colonne supprimée, aucune donnée recopiée, aucune table créée.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_composition"
down_revision = "0008_identite_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matchs", sa.Column("formation_domicile", sa.String(length=12), nullable=True))
    op.add_column("matchs", sa.Column("formation_exterieur", sa.String(length=12), nullable=True))
    op.add_column("matchs", sa.Column("staff_domicile_id", sa.Integer(), nullable=True))
    op.add_column("matchs", sa.Column("staff_exterieur_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_matchs_staff_domicile",
        "matchs",
        "staffs",
        ["staff_domicile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_matchs_staff_exterieur",
        "matchs",
        "staffs",
        ["staff_exterieur_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("competitions", sa.Column("max_remplacants", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("competitions", "max_remplacants")
    op.drop_constraint("fk_matchs_staff_exterieur", "matchs", type_="foreignkey")
    op.drop_constraint("fk_matchs_staff_domicile", "matchs", type_="foreignkey")
    op.drop_column("matchs", "staff_exterieur_id")
    op.drop_column("matchs", "staff_domicile_id")
    op.drop_column("matchs", "formation_exterieur")
    op.drop_column("matchs", "formation_domicile")
