"""Actualités, images éditoriales, likes et Homme du match.

Revision ID: 0015_actualites_annonces
Revises: 0014_effectifs_obligatoires
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_actualites_annonces"
down_revision = "0014_effectifs_obligatoires"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actualites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titre", sa.String(length=180), nullable=False),
        sa.Column("categorie", sa.String(length=40), nullable=False),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column("statut", sa.String(length=20), server_default="brouillon", nullable=False),
        sa.Column("telechargement_autorise", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("auteur_id", sa.Integer(), nullable=True),
        sa.Column("competition_id", sa.Integer(), nullable=True),
        sa.Column("saison_id", sa.Integer(), nullable=True),
        sa.Column("journee", sa.String(length=30), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("club_id", sa.Integer(), nullable=True),
        sa.Column("joueur_id", sa.Integer(), nullable=True),
        sa.Column("date_creation", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("date_modification", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_publication", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("statut IN ('brouillon','publie','archive')", name="ck_actualites_statut"),
        sa.CheckConstraint(
            "categorie IN ('annonce','match_competition','retour_journee','homme_du_match','performance','photo_moment','fair_play','information_importante')",
            name="ck_actualites_categorie",
        ),
        sa.ForeignKeyConstraint(["auteur_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["saison_id"], ["saisons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["matchs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["joueur_id"], ["joueurs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, column in (
        ("ix_actualites_statut", "statut"),
        ("ix_actualites_categorie", "categorie"),
        ("ix_actualites_auteur_id", "auteur_id"),
        ("ix_actualites_competition_id", "competition_id"),
        ("ix_actualites_saison_id", "saison_id"),
        ("ix_actualites_match_id", "match_id"),
        ("ix_actualites_club_id", "club_id"),
        ("ix_actualites_joueur_id", "joueur_id"),
        ("ix_actualites_date_publication", "date_publication"),
    ):
        op.create_index(name, "actualites", [column])

    op.create_table(
        "actualite_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actualite_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=300), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("ordre", sa.Integer(), server_default="0", nullable=False),
        sa.Column("principale", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actualite_id"], ["actualites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actualite_images_actualite_id", "actualite_images", ["actualite_id"])

    op.create_table(
        "actualite_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actualite_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actualite_id"], ["actualites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actualite_id", "token_hash", name="uq_actualite_likes_actualite_token"),
    )
    op.create_index("ix_actualite_likes_actualite_id", "actualite_likes", ["actualite_id"])

    op.create_table(
        "hommes_match",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("joueur_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("designe_par_id", sa.Integer(), nullable=True),
        sa.Column("designe_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matchs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["joueur_id"], ["joueurs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["designe_par_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", name="uq_hommes_match_match"),
    )
    op.create_index("ix_hommes_match_match_id", "hommes_match", ["match_id"])
    op.create_index("ix_hommes_match_joueur_id", "hommes_match", ["joueur_id"])


def downgrade() -> None:
    op.drop_index("ix_hommes_match_joueur_id", table_name="hommes_match")
    op.drop_index("ix_hommes_match_match_id", table_name="hommes_match")
    op.drop_table("hommes_match")
    op.drop_index("ix_actualite_likes_actualite_id", table_name="actualite_likes")
    op.drop_table("actualite_likes")
    op.drop_index("ix_actualite_images_actualite_id", table_name="actualite_images")
    op.drop_table("actualite_images")
    for name in (
        "ix_actualites_date_publication",
        "ix_actualites_joueur_id",
        "ix_actualites_club_id",
        "ix_actualites_match_id",
        "ix_actualites_saison_id",
        "ix_actualites_competition_id",
        "ix_actualites_auteur_id",
        "ix_actualites_categorie",
        "ix_actualites_statut",
    ):
        op.drop_index(name, table_name="actualites")
    op.drop_table("actualites")
