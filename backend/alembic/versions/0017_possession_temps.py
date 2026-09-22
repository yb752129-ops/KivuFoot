"""Ajoute Possession V1 fondée sur le temps observé.

Revision ID: 0017_possession_temps
Revises: 0016_actualites_mise_en_avant
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0017_possession_temps"
down_revision = "0016_actualites_mise_en_avant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "possessions_matchs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("equipe_a_id", sa.Integer(), sa.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("equipe_b_id", sa.Integer(), sa.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("methode", sa.String(length=30), nullable=False, server_default="TIME_BASED"),
        sa.Column(
            "protocole",
            sa.String(length=60),
            nullable=False,
            server_default="KIVUFOOT_POSSESSION_V1",
        ),
        sa.Column("etat_courant", sa.String(length=20), nullable=False, server_default="NOT_STARTED"),
        sa.Column("pause_hors_jeu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="PROVISOIRE"),
        sa.Column("temps_a_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("temps_b_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("temps_non_attribue_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("nombre_changements", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nombre_sequences_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nombre_sequences_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collecteur_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("valide_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("officialisee_at", sa.DateTime(timezone=True)),
        sa.Column("derniere_transition_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("eligible_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("motif_exclusion_public", sa.String(length=255)),
        sa.UniqueConstraint("match_id", name="uq_possessions_matchs_match_id"),
        sa.CheckConstraint("equipe_a_id <> equipe_b_id", name="ck_possession_equipes_differentes"),
        sa.CheckConstraint(
            "temps_a_ms >= 0 AND temps_b_ms >= 0 AND temps_non_attribue_ms >= 0",
            name="ck_possession_temps_non_negatifs",
        ),
        sa.CheckConstraint(
            "etat_courant IN ('TEAM_A', 'TEAM_B', 'PAUSE', 'NOT_STARTED', 'FINISHED')",
            name="ck_possession_etat_courant",
        ),
        sa.CheckConstraint(
            "statut IN ('PROVISOIRE', 'OFFICIELLE')",
            name="ck_possession_statut",
        ),
        sa.CheckConstraint("methode = 'TIME_BASED'", name="ck_possession_methode_v1"),
        sa.CheckConstraint(
            "protocole = 'KIVUFOOT_POSSESSION_V1'",
            name="ck_possession_protocole_v1",
        ),
    )
    op.create_index("ix_possessions_matchs_match_id", "possessions_matchs", ["match_id"])

    op.create_table(
        "possession_intervalles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "possession_id",
            sa.Integer(),
            sa.ForeignKey("possessions_matchs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("etat", sa.String(length=20), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("debut_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin_at", sa.DateTime(timezone=True)),
        sa.Column("duree_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("periode", sa.String(length=12)),
        sa.Column("cree_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint(
            "etat IN ('TEAM_A', 'TEAM_B', 'PAUSE')",
            name="ck_possession_intervalle_etat",
        ),
        sa.CheckConstraint("duree_ms >= 0", name="ck_possession_intervalle_duree_non_negative"),
        sa.CheckConstraint("sequence_no > 0", name="ck_possession_intervalle_sequence_positive"),
    )
    op.create_index("ix_possession_intervalles_possession_id", "possession_intervalles", ["possession_id"])
    op.create_index(
        "ix_possession_intervalles_ouvert",
        "possession_intervalles",
        ["possession_id", "fin_at"],
    )

    op.create_table(
        "possession_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "possession_id",
            sa.Integer(),
            sa.ForeignKey("possessions_matchs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intervalle_id",
            sa.Integer(),
            sa.ForeignKey("possession_intervalles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ancien_etat", sa.String(length=20), nullable=False),
        sa.Column("ancien_debut_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ancien_fin_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ancien_duree_ms", sa.BigInteger(), nullable=False),
        sa.Column("nouvel_etat", sa.String(length=20), nullable=False),
        sa.Column("nouveau_debut_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nouveau_fin_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nouvelle_duree_ms", sa.BigInteger(), nullable=False),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column("corrige_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("operation_id", name="uq_possession_corrections_operation_id"),
        sa.CheckConstraint(
            "ancien_duree_ms >= 0 AND nouvelle_duree_ms >= 0",
            name="ck_possession_correction_durees_non_negatives",
        ),
        sa.CheckConstraint(
            "nouvel_etat IN ('TEAM_A', 'TEAM_B', 'PAUSE')",
            name="ck_possession_correction_etat",
        ),
    )
    op.create_index("ix_possession_corrections_possession_id", "possession_corrections", ["possession_id"])

    op.create_table(
        "possession_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "possession_id",
            sa.Integer(),
            sa.ForeignKey("possessions_matchs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("etat_demande", sa.String(length=20), nullable=False),
        sa.Column("etat_avant", sa.String(length=20), nullable=False),
        sa.Column("etat_apres", sa.String(length=20), nullable=False),
        sa.Column("appliquee_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cree_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("correction", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("operation_id", name="uq_possession_operations_operation_id"),
        sa.CheckConstraint(
            "etat_demande IN ('TEAM_A', 'TEAM_B', 'PAUSE', 'FINISHED')",
            name="ck_possession_operation_demande",
        ),
    )
    op.create_index("ix_possession_operations_possession_id", "possession_operations", ["possession_id"])


def downgrade() -> None:
    op.drop_index("ix_possession_operations_possession_id", table_name="possession_operations")
    op.drop_table("possession_operations")
    op.drop_index("ix_possession_corrections_possession_id", table_name="possession_corrections")
    op.drop_table("possession_corrections")
    op.drop_index("ix_possession_intervalles_ouvert", table_name="possession_intervalles")
    op.drop_index("ix_possession_intervalles_possession_id", table_name="possession_intervalles")
    op.drop_table("possession_intervalles")
    op.drop_index("ix_possessions_matchs_match_id", table_name="possessions_matchs")
    op.drop_table("possessions_matchs")
