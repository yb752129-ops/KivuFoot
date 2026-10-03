"""Ajoute le registre des documents officiels versionnés.

Revision ID: 0020_documents_officiels
Revises: 0019_moteur_sportif_p0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020_documents_officiels"
down_revision = "0019_moteur_sportif_p0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents_officiels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type_document", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="genere"),
        sa.Column("titre", sa.String(length=255), nullable=False),
        sa.Column("empreinte_source", sa.String(length=64), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("message_erreur", sa.Text(), nullable=True),
        sa.Column("genere_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("publie_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("remplace_document_id", sa.Integer(), sa.ForeignKey("documents_officiels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("type_document", "scope_id", "competition_id", "saison_id", "statut", "empreinte_source"):
        op.create_index(f"ix_documents_officiels_{column}", "documents_officiels", [column])


def downgrade() -> None:
    for column in ("type_document", "scope_id", "competition_id", "saison_id", "statut", "empreinte_source"):
        op.drop_index(f"ix_documents_officiels_{column}", table_name="documents_officiels")
    op.drop_table("documents_officiels")
