"""Allow express registration of a player before the birth date is known.

Revision ID: 0023_joueur_date_optional
Revises: 0022_role_club

This is a schema-only relaxation for the live-match emergency flow. Existing
rows are untouched. Missing dates remain visible as incomplete identity data
and are not silently replaced with a fabricated date.
"""

from alembic import op
import sqlalchemy as sa

revision = "0023_joueur_date_optional"
down_revision = "0022_role_club"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "joueurs",
        "date_naissance",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    missing_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM joueurs WHERE date_naissance IS NULL")
    ).scalar_one()
    if missing_count:
        raise RuntimeError(
            "Downgrade 0023 refused: joueurs without date_naissance exist; "
            "no date is fabricated or data row is modified automatically."
        )
    op.alter_column(
        "joueurs",
        "date_naissance",
        existing_type=sa.Date(),
        nullable=False,
    )
