"""Add a reversible administrative status to each season club.

Revision ID: 0026_statut_equipe_edition
Revises: 0025_match_annulation

The migration only adds nullable/a-default metadata. It deliberately does
not decide a business status for any club: every existing registration is
created as ``actif`` by the database default and no match is touched.
"""

from alembic import op
import sqlalchemy as sa

revision = "0026_statut_equipe_edition"
down_revision = "0025_match_annulation"
branch_labels = None
depends_on = None

STATUTS = "'actif','disqualifie','elimine','retire'"


def upgrade() -> None:
    op.add_column(
        "saison_clubs",
        sa.Column("statut", sa.String(20), nullable=False, server_default=sa.text("'actif'")),
    )
    op.add_column(
        "saison_clubs",
        sa.Column("statut_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )
    op.add_column("saison_clubs", sa.Column("statut_motif", sa.String(500), nullable=True))
    op.add_column(
        "saison_clubs",
        sa.Column(
            "statut_modifie_par_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_saison_clubs_statut", "saison_clubs", ["statut"])
    op.create_check_constraint(
        "ck_saison_clubs_statut",
        "saison_clubs",
        f"statut IN ({STATUTS})",
    )


def downgrade() -> None:
    bind = op.get_bind()
    non_actifs = bind.execute(
        sa.text("SELECT COUNT(*) FROM saison_clubs WHERE statut <> 'actif'")
    ).scalar_one()
    if non_actifs:
        raise RuntimeError(
            "Downgrade 0026 refused: non-active team decisions still exist; "
            "restore those teams through the admin action before rolling back."
        )

    op.drop_constraint("ck_saison_clubs_statut", "saison_clubs", type_="check")
    op.drop_index("ix_saison_clubs_statut", table_name="saison_clubs")
    op.drop_column("saison_clubs", "statut_modifie_par_id")
    op.drop_column("saison_clubs", "statut_motif")
    op.drop_column("saison_clubs", "statut_at")
    op.drop_column("saison_clubs", "statut")
