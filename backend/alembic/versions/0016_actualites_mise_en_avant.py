"""Ajoute la priorité éditoriale des actualités.

Revision ID: 0016_actualites_mise_en_avant
Revises: 0015_actualites_annonces
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_actualites_mise_en_avant"
down_revision = "0015_actualites_annonces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "actualites",
        sa.Column("mise_en_avant", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_actualites_mise_en_avant", "actualites", ["mise_en_avant"])


def downgrade() -> None:
    op.drop_index("ix_actualites_mise_en_avant", table_name="actualites")
    op.drop_column("actualites", "mise_en_avant")
