"""Ajoute le socle versionné et non destructif du moteur sportif P0.

Aucune donnée historique n'est rétro-rattachée à un règlement dans cette
migration. Les nouvelles colonnes de liaison restent NULL jusqu'à décision
explicite du Comité d'Organisation.

Revision ID: 0019_moteur_sportif_p0
Revises: 0018_actualites_lectures
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_moteur_sportif_p0"
down_revision = "0018_actualites_lectures"
branch_labels = None
depends_on = None


def _jsonb():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "reglements_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=32), nullable=False, server_default="brouillon"),
        sa.Column("schema_version", sa.String(length=20), nullable=False, server_default="1"),
        sa.Column("configuration", _jsonb(), nullable=False),
        sa.Column("source_officielle", sa.Text(), nullable=True),
        sa.Column("reference_decision", sa.String(length=255), nullable=True),
        sa.Column("date_effet", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("cree_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("active_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("saison_id", "version", name="uq_reglement_saison_version"),
    )
    op.create_index("ix_reglements_versions_competition_id", "reglements_versions", ["competition_id"])
    op.create_index("ix_reglements_versions_saison_id", "reglements_versions", ["saison_id"])
    op.create_index("ix_reglements_versions_statut", "reglements_versions", ["statut"])

    op.create_table(
        "effectifs_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("club_id", sa.Integer(), sa.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=32), nullable=False, server_default="brouillon"),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("soumis_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("valide_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("soumis_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valide_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_effet", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("saison_id", "club_id", "version", name="uq_effectif_version_saison_club"),
    )
    op.create_index("ix_effectifs_versions_saison_id", "effectifs_versions", ["saison_id"])
    op.create_index("ix_effectifs_versions_club_id", "effectifs_versions", ["club_id"])
    op.create_index("ix_effectifs_versions_statut", "effectifs_versions", ["statut"])

    op.create_table(
        "effectifs_versions_joueurs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("effectif_version_id", sa.Integer(), sa.ForeignKey("effectifs_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joueur_id", sa.Integer(), sa.ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("motif", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("effectif_version_id", "joueur_id", name="uq_effectif_version_joueur"),
    )
    op.create_index("ix_effectifs_versions_joueurs_effectif_version_id", "effectifs_versions_joueurs", ["effectif_version_id"])
    op.create_index("ix_effectifs_versions_joueurs_joueur_id", "effectifs_versions_joueurs", ["joueur_id"])

    op.create_table(
        "sanctions_disciplinaires",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("joueur_id", sa.Integer(), sa.ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reglement_version_id", sa.Integer(), sa.ForeignKey("reglements_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("evenement_declencheur_id", sa.Integer(), sa.ForeignKey("evenements_match.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("type_motif", sa.String(length=50), nullable=False),
        sa.Column("statut", sa.String(length=32), nullable=False, server_default="calculee"),
        sa.Column("nombre_matchs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matchs_restants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explication", sa.Text(), nullable=False),
        sa.Column("configuration_snapshot", _jsonb(), nullable=True),
        sa.Column("empreinte_source", sa.String(length=64), nullable=True),
        sa.Column("date_effet", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("competition_id", "saison_id", "joueur_id", "reglement_version_id", "evenement_declencheur_id", "statut", "empreinte_source"):
        op.create_index(f"ix_sanctions_disciplinaires_{column}", "sanctions_disciplinaires", [column])

    op.create_table(
        "sanctions_matchs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sanction_id", sa.Integer(), sa.ForeignKey("sanctions_disciplinaires.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="a_servir"),
        sa.UniqueConstraint("sanction_id", "match_id", name="uq_sanction_match"),
    )
    op.create_index("ix_sanctions_matchs_sanction_id", "sanctions_matchs", ["sanction_id"])
    op.create_index("ix_sanctions_matchs_match_id", "sanctions_matchs", ["match_id"])

    op.create_table(
        "anomalies_historiques",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("joueur_id", sa.Integer(), sa.ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("club_id", sa.Integer(), sa.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("type_anomalie", sa.String(length=64), nullable=False),
        sa.Column("severite", sa.String(length=20), nullable=False, server_default="attention"),
        sa.Column("statut", sa.String(length=40), nullable=False, server_default="a_examiner"),
        sa.Column("observation", _jsonb(), nullable=False),
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("decide_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decide_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("saison_id", "match_id", "type_anomalie", "empreinte", name="uq_anomalie_observation"),
    )
    for column in ("saison_id", "match_id", "joueur_id", "club_id", "statut"):
        op.create_index(f"ix_anomalies_historiques_{column}", "anomalies_historiques", [column])

    op.create_table(
        "decisions_sportives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("saison_id", sa.Integer(), sa.ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("joueur_id", sa.Integer(), sa.ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("club_id", sa.Integer(), sa.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sanction_id", sa.Integer(), sa.ForeignKey("sanctions_disciplinaires.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("anomalie_id", sa.Integer(), sa.ForeignKey("anomalies_historiques.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("type_decision", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="confirmee"),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column("details", _jsonb(), nullable=True),
        sa.Column("decide_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("competition_id", "saison_id", "match_id", "joueur_id", "club_id", "sanction_id", "anomalie_id"):
        op.create_index(f"ix_decisions_sportives_{column}", "decisions_sportives", [column])

    op.create_table(
        "controles_validation_matchs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reglement_version_id", sa.Integer(), sa.ForeignKey("reglements_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("resultat", sa.String(length=20), nullable=False),
        sa.Column("empreinte_source", sa.String(length=64), nullable=True),
        sa.Column("controles", _jsonb(), nullable=False),
        sa.Column("execute_par_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_controles_validation_matchs_match_id", "controles_validation_matchs", ["match_id"])
    op.create_index("ix_controles_validation_matchs_reglement_version_id", "controles_validation_matchs", ["reglement_version_id"])

    op.add_column(
        "matchs",
        sa.Column("reglement_version_id", sa.Integer(), sa.ForeignKey("reglements_versions.id", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_matchs_reglement_version_id", "matchs", ["reglement_version_id"])


def downgrade() -> None:
    op.drop_index("ix_matchs_reglement_version_id", table_name="matchs")
    op.drop_column("matchs", "reglement_version_id")
    op.drop_index("ix_controles_validation_matchs_reglement_version_id", table_name="controles_validation_matchs")
    op.drop_index("ix_controles_validation_matchs_match_id", table_name="controles_validation_matchs")
    op.drop_table("controles_validation_matchs")
    for column in ("competition_id", "saison_id", "match_id", "joueur_id", "club_id", "sanction_id", "anomalie_id"):
        op.drop_index(f"ix_decisions_sportives_{column}", table_name="decisions_sportives")
    op.drop_table("decisions_sportives")
    for column in ("saison_id", "match_id", "joueur_id", "club_id", "statut"):
        op.drop_index(f"ix_anomalies_historiques_{column}", table_name="anomalies_historiques")
    op.drop_table("anomalies_historiques")
    op.drop_index("ix_sanctions_matchs_match_id", table_name="sanctions_matchs")
    op.drop_index("ix_sanctions_matchs_sanction_id", table_name="sanctions_matchs")
    op.drop_table("sanctions_matchs")
    for column in ("competition_id", "saison_id", "joueur_id", "reglement_version_id", "evenement_declencheur_id", "statut", "empreinte_source"):
        op.drop_index(f"ix_sanctions_disciplinaires_{column}", table_name="sanctions_disciplinaires")
    op.drop_table("sanctions_disciplinaires")
    op.drop_index("ix_effectifs_versions_joueurs_joueur_id", table_name="effectifs_versions_joueurs")
    op.drop_index("ix_effectifs_versions_joueurs_effectif_version_id", table_name="effectifs_versions_joueurs")
    op.drop_table("effectifs_versions_joueurs")
    op.drop_index("ix_effectifs_versions_statut", table_name="effectifs_versions")
    op.drop_index("ix_effectifs_versions_club_id", table_name="effectifs_versions")
    op.drop_index("ix_effectifs_versions_saison_id", table_name="effectifs_versions")
    op.drop_table("effectifs_versions")
    op.drop_index("ix_reglements_versions_statut", table_name="reglements_versions")
    op.drop_index("ix_reglements_versions_saison_id", table_name="reglements_versions")
    op.drop_index("ix_reglements_versions_competition_id", table_name="reglements_versions")
    op.drop_table("reglements_versions")
