"""Ajoute le suivi de lecture anonyme des actualités.

Revision ID: 0018_actualites_lectures
Revises: 0017_possession_temps
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_actualites_lectures"
down_revision = "0017_possession_temps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actualite_lectures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "actualite_id",
            sa.Integer(),
            sa.ForeignKey("actualites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "date_lecture",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "actualite_id",
            "token_hash",
            name="uq_actualite_lectures_actualite_token",
        ),
    )
    op.create_index(
        "ix_actualite_lectures_actualite_id",
        "actualite_lectures",
        ["actualite_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_actualite_lectures_actualite_id", table_name="actualite_lectures")
    op.drop_table("actualite_lectures")
