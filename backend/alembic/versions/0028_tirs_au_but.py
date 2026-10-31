"""Store knockout shootout kicks separately from match events and score.

Revision ID: 0028_tirs_au_but
Revises: 0027_phase_barrage
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0028_tirs_au_but"
down_revision = "0027_phase_barrage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matchs",
        sa.Column(
            "tirs_au_but",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("matchs", "tirs_au_but")
