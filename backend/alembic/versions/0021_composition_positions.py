"""Ajoute la place tactique propre à chaque participation de composition.

Revision ID: 0021_composition_positions
Revises: 0020_documents_officiels

Migration additive et compatible : les anciennes participations conservent
leurs statuts et leurs numéros, avec une place NULL à compléter explicitement.
Aucune position n'est inventée à partir du poste habituel.
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_composition_positions"
down_revision = "0020_documents_officiels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("match_participations", sa.Column("ligne_index", sa.Integer(), nullable=True))
    op.add_column("match_participations", sa.Column("position_index", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_participation_position_pair",
        "match_participations",
        "(ligne_index IS NULL AND position_index IS NULL) OR "
        "(ligne_index IS NOT NULL AND position_index IS NOT NULL AND ligne_index >= 0 AND position_index >= 0)",
    )
    op.create_unique_constraint(
        "uq_match_participation_position",
        "match_participations",
        ["match_id", "equipe_concernee", "ligne_index", "position_index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_match_participation_position", "match_participations", type_="unique")
    op.drop_constraint("ck_participation_position_pair", "match_participations", type_="check")
    op.drop_column("match_participations", "position_index")
    op.drop_column("match_participations", "ligne_index")
