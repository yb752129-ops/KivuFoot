"""Workflow obligatoire de soumission des effectifs par club.

Revision ID: 0014_effectifs_obligatoires
Revises: 0013_resultat_retroactif
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_effectifs_obligatoires"
down_revision = "0013_resultat_retroactif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "effectifs_clubs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("saison_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="a_completer"),
        sa.Column("soumis_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("soumis_par_id", sa.Integer(), nullable=True),
        sa.Column("traite_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("traite_par_id", sa.Integer(), nullable=True),
        sa.Column("motif_retour", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "statut IN ('a_completer','en_cours','soumis','a_corriger','valide')",
            name="ck_effectifs_clubs_statut",
        ),
        sa.ForeignKeyConstraint(["saison_id"], ["saisons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["soumis_par_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["traite_par_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("saison_id", "club_id", name="uq_effectifs_clubs_saison_club"),
    )
    op.create_index("ix_effectifs_clubs_saison_id", "effectifs_clubs", ["saison_id"])
    op.create_index("ix_effectifs_clubs_club_id", "effectifs_clubs", ["club_id"])


def downgrade() -> None:
    op.drop_index("ix_effectifs_clubs_club_id", table_name="effectifs_clubs")
    op.drop_index("ix_effectifs_clubs_saison_id", table_name="effectifs_clubs")
    op.drop_table("effectifs_clubs")
