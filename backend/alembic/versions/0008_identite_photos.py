"""Identité des personnes et photos versionnées.

Revision ID: 0008_identite_photos
Revises: 0007_poules

Ajouts non destructifs :
- joueurs.statut (actif/suspendu/inactif/transfere/libere/retire), joueurs.updated_at,
  joueurs.photo_actuelle_id ;
- table staffs (entité personne du staff, rôles extensibles) ;
- table photos (versioning, statuts en_attente/validee/rejetee, motif de refus).
Aucune colonne supprimée, aucune donnée recopiée.
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_identite_photos"
down_revision = "0007_poules"
branch_labels = None
depends_on = None

STATUT_PERSONNE = "statut IN ('actif','suspendu','inactif','transfere','libere','retire')"


def upgrade() -> None:
    op.create_table(
        "staffs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("club_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nom_complet", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("statut", sa.String(12), nullable=False, server_default="actif"),
        sa.Column("photo_actuelle_id", sa.Integer, sa.ForeignKey("photos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_staffs_club_id", "staffs", ["club_id"])
    op.create_check_constraint(
        "ck_staffs_role",
        "staffs",
        "role IN ('entraineur_principal','adjoint','entraineur_gardiens',"
        "'preparateur_physique','analyste','team_manager','medical','autre')",
    )
    op.create_check_constraint("ck_staffs_statut", "staffs", STATUT_PERSONNE)

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sujet_type", sa.String(10), nullable=False),
        sa.Column("sujet_id", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("statut", sa.String(12), nullable=False, server_default="en_attente"),
        sa.Column("reviewed_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motif_refus", sa.String(30), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_photos_sujet", "photos", ["sujet_type", "sujet_id"])
    op.create_check_constraint("ck_photos_sujet_type", "photos", "sujet_type IN ('joueur','staff')")
    op.create_check_constraint(
        "ck_photos_statut", "photos", "statut IN ('en_attente','validee','rejetee')"
    )
    op.create_check_constraint(
        "ck_photos_motif",
        "photos",
        "motif_refus IS NULL OR motif_refus IN ('visage_non_visible','photo_trop_floue',"
        "'mauvaise_personne','photo_non_conforme','autre')",
    )

    op.add_column(
        "joueurs",
        sa.Column("statut", sa.String(12), nullable=False, server_default="actif"),
    )
    op.create_check_constraint("ck_joueurs_statut", "joueurs", STATUT_PERSONNE)
    op.add_column("joueurs", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "joueurs",
        sa.Column("photo_actuelle_id", sa.Integer, sa.ForeignKey("photos.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("joueurs", "photo_actuelle_id")
    op.drop_column("joueurs", "updated_at")
    op.drop_constraint("ck_joueurs_statut", "joueurs", type_="check")
    op.drop_column("joueurs", "statut")
    op.drop_constraint("ck_photos_motif", "photos", type_="check")
    op.drop_constraint("ck_photos_statut", "photos", type_="check")
    op.drop_constraint("ck_photos_sujet_type", "photos", type_="check")
    op.drop_index("ix_photos_sujet", "photos")
    op.drop_table("photos")
    op.drop_constraint("ck_staffs_statut", "staffs", type_="check")
    op.drop_constraint("ck_staffs_role", "staffs", type_="check")
    op.drop_index("ix_staffs_club_id", "staffs")
    op.drop_table("staffs")
