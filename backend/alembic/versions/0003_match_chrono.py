"""Coup d'envoi et fin de match (chrono réel).

Revision ID: 0003_match_chrono
Revises: 0002_supporter
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_match_chrono"
down_revision = "0002_supporter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matchs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("matchs", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("matchs", "ended_at")
    op.drop_column("matchs", "started_at")
