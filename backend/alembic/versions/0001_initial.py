"""schema initial KivuFoot (corrigé Phase 0)

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("mot_de_passe_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("nom_complet", sa.String(255)),
        sa.Column("club_id", sa.Integer),  # FK ajoutée après création de clubs
        sa.Column("est_actif", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "role IN ('collecteur','organisateur','club_manager','admin')", name="ck_users_role"
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # --- clubs -----------------------------------------------------------
    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("stade", sa.String(255)),
        sa.Column("ville", sa.String(100), nullable=False),
        sa.Column("logo_url", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clubs_nom", "clubs", ["nom"])

    op.create_foreign_key("fk_users_club", "users", "clubs", ["club_id"], ["id"], ondelete="SET NULL")

    # --- refresh_tokens ----------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- competitions --------------------------------------------------
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("saison", sa.String(50)),
        sa.Column("est_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("est_demo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('championnat','coupe','tournoi')", name="ck_competitions_type"),
    )
    op.create_index("ix_competitions_est_demo", "competitions", ["est_demo"])

    # --- saisons ---------------------------------------------------------
    op.create_table(
        "saisons",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("competition_id", sa.Integer, sa.ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nom", sa.String(100)),
        sa.Column("date_debut", sa.Date),
        sa.Column("date_fin", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- saison_clubs ------------------------------------------------------
    op.create_table(
        "saison_clubs",
        sa.Column("saison_id", sa.Integer, sa.ForeignKey("saisons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("club_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- organisateur_competitions (ajout Phase 0) --------------------------
    op.create_table(
        "organisateur_competitions",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("competition_id", sa.Integer, sa.ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- joueurs (avec champs ajoutés Phase 0) ------------------------------
    op.create_table(
        "joueurs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nom_complet", sa.String(255), nullable=False),
        sa.Column("date_naissance", sa.Date, nullable=False),
        sa.Column("poste", sa.String(50)),
        sa.Column("club_actuel_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="SET NULL")),
        sa.Column("telephone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("statut_verification", sa.String(30), nullable=False, server_default="verifie"),
        sa.Column("fusionne", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("fusionne_vers_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="SET NULL")),
        sa.Column("autorisation_parentale", sa.Boolean),
        sa.Column("anonymise", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("poste IN ('gardien','defenseur','milieu','attaquant') OR poste IS NULL", name="ck_joueurs_poste"),
        sa.CheckConstraint(
            "statut_verification IN ('verifie','en_attente_verification','doublon_suspecte')",
            name="ck_joueurs_statut_verification",
        ),
    )
    op.create_index("ix_joueurs_nom_complet", "joueurs", ["nom_complet"])

    # --- joueurs_modifications_proposees (workflow décision C1) -----------
    op.create_table(
        "joueurs_modifications_proposees",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("joueur_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposee_par_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("champ", sa.String(50), nullable=False),
        sa.Column("ancienne_valeur", sa.String(255)),
        sa.Column("nouvelle_valeur", sa.String(255), nullable=False),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_attente"),
        sa.Column("traitee_par_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("date_traitement", sa.DateTime(timezone=True)),
        sa.Column("commentaire", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("statut IN ('en_attente','approuvee','rejetee')", name="ck_modif_proposee_statut"),
    )

    # --- matchs (avec forfait/locked corrigés Phase 0) ----------------------
    op.create_table(
        "matchs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("saison_id", sa.Integer, sa.ForeignKey("saisons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("journee", sa.String(20)),
        sa.Column("date_heure", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stade", sa.String(255)),
        sa.Column("equipe_domicile_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="SET NULL")),
        sa.Column("equipe_exterieur_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="SET NULL")),
        sa.Column("score_domicile", sa.Integer, nullable=False, server_default="0"),
        sa.Column("score_exterieur", sa.Integer, nullable=False, server_default="0"),
        sa.Column("statut", sa.String(20), nullable=False, server_default="programme"),
        sa.Column("forfait", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("forfait_equipe", sa.String(10)),
        sa.Column("valide_par", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("date_validation", sa.DateTime(timezone=True)),
        sa.Column("locked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "statut IN ('programme','en_cours','termine','valide','conteste')", name="ck_matchs_statut"
        ),
        sa.CheckConstraint(
            "forfait_equipe IN ('domicile','exterieur') OR forfait_equipe IS NULL", name="ck_matchs_forfait_equipe"
        ),
        sa.CheckConstraint(
            "equipe_domicile_id IS NULL OR equipe_exterieur_id IS NULL OR equipe_domicile_id != equipe_exterieur_id",
            name="ck_match_equipes_differentes",
        ),
    )
    op.create_index("ix_matchs_saison_id", "matchs", ["saison_id"])
    op.create_index("ix_matchs_statut", "matchs", ["statut"])

    # --- match_participations (ajout Phase 0 : feuille de match) -----------
    op.create_table(
        "match_participations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("match_id", sa.Integer, sa.ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joueur_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("club_id", sa.Integer, sa.ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("equipe_concernee", sa.String(10), nullable=False),
        sa.Column("statut", sa.String(20), nullable=False),
        sa.Column("minute_entree", sa.Integer, nullable=False, server_default="0"),
        sa.Column("minute_sortie", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("equipe_concernee IN ('domicile','exterieur')", name="ck_participation_equipe"),
        sa.CheckConstraint("statut IN ('titulaire','remplacant')", name="ck_participation_statut"),
        sa.UniqueConstraint("match_id", "joueur_id", name="uq_participation_match_joueur"),
    )

    # --- evenements_match (corrections majeures Phase 0 - point A1) --------
    op.create_table(
        "evenements_match",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("match_id", sa.Integer, sa.ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("minute", sa.Integer, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("joueur_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="SET NULL")),
        sa.Column("joueur_secondaire_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="SET NULL")),
        sa.Column("resultat", sa.String(10)),
        sa.Column("equipe_concernee", sa.String(10), nullable=False),
        sa.Column("statut_validation", sa.String(20), nullable=False, server_default="en_attente"),
        sa.Column("valide_par", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("date_validation", sa.DateTime(timezone=True)),
        sa.Column("commentaire_rejet", sa.Text),
        sa.Column("conflit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("locked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(50), nullable=False, server_default="collecteur_mobile"),
        sa.Column("temp_id", postgresql.UUID(as_uuid=True), unique=True),
        sa.Column("cree_par_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("minute >= 0", name="ck_evenement_minute_positive"),
        sa.CheckConstraint(
            "type IN ('but','but_contre_son_camp','passe_decisive','carton_jaune','carton_rouge','remplacement','penalty')",
            name="ck_evenement_type",
        ),
        sa.CheckConstraint("equipe_concernee IN ('domicile','exterieur')", name="ck_evenement_equipe"),
        # NB : 'brut' volontairement absent - concept client uniquement (rapport Phase 0, point A2).
        sa.CheckConstraint(
            "statut_validation IN ('en_attente','valide','rejete')", name="ck_evenement_statut_validation"
        ),
        sa.CheckConstraint("resultat IN ('marque','rate') OR resultat IS NULL", name="ck_evenement_resultat"),
    )
    op.create_index("ix_evenements_match_id", "evenements_match", ["match_id"])
    op.create_index("ix_evenements_statut_validation", "evenements_match", ["statut_validation"])
    op.create_index("ix_evenements_temp_id", "evenements_match", ["temp_id"])

    # --- audit_log ---------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("table_name", sa.String(50), nullable=False),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("old_data", postgresql.JSONB),
        sa.Column("new_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "action IN ('INSERT','UPDATE','DELETE','VALIDATE','REJECT','MERGE')", name="ck_audit_action"
        ),
    )
    op.create_index("ix_audit_log_table_name", "audit_log", ["table_name"])
    op.create_index("ix_audit_log_record_id", "audit_log", ["record_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # --- stockage_synchronisation (temp_id idempotent - ajout Phase 0) -----
    op.create_table(
        "stockage_synchronisation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("utilisateur_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("temp_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("donnees", postgresql.JSONB, nullable=False),
        sa.Column("statut", sa.String(20), nullable=False, server_default="local"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('evenement','match','joueur')", name="ck_sync_type"),
        sa.CheckConstraint("statut IN ('local','envoye','confirme')", name="ck_sync_statut"),
        sa.UniqueConstraint("utilisateur_id", "temp_id", name="uq_sync_utilisateur_temp_id"),
    )

    # --- conflits_synchronisation (ajout Phase 0 - table manquante) --------
    op.create_table(
        "conflits_synchronisation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("evenement_id", sa.Integer, sa.ForeignKey("evenements_match.id", ondelete="CASCADE")),
        sa.Column("version_a", postgresql.JSONB, nullable=False),
        sa.Column("version_b", postgresql.JSONB, nullable=False),
        sa.Column("utilisateur_a_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("utilisateur_b_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_attente"),
        sa.Column("resolu_par_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolution", postgresql.JSONB),
        sa.Column("date_resolution", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("statut IN ('en_attente','resolu')", name="ck_conflit_statut"),
    )

    # --- consentements (ajout Phase 0 - table formalisée) -------------------
    op.create_table(
        "consentements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("joueur_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("valide", sa.Boolean, nullable=False),
        sa.Column("date_consentement", sa.Date, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('public','stats','contact')", name="ck_consentement_type"),
    )

    # --- statistiques_joueurs (clé composite corrigée Phase 0 - point A4) --
    op.create_table(
        "statistiques_joueurs",
        sa.Column("joueur_id", sa.Integer, sa.ForeignKey("joueurs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("competition_id", sa.Integer, sa.ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("saison_id", sa.Integer, sa.ForeignKey("saisons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("matchs_joues", sa.Integer, nullable=False, server_default="0"),
        sa.Column("titularisations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("buts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passes_decisives", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cartons_jaunes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cartons_rouges", sa.Integer, nullable=False, server_default="0"),
        sa.Column("minutes_jouees", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("statistiques_joueurs")
    op.drop_table("consentements")
    op.drop_table("conflits_synchronisation")
    op.drop_table("stockage_synchronisation")
    op.drop_table("audit_log")
    op.drop_table("evenements_match")
    op.drop_table("match_participations")
    op.drop_table("matchs")
    op.drop_table("joueurs_modifications_proposees")
    op.drop_table("joueurs")
    op.drop_table("organisateur_competitions")
    op.drop_table("saison_clubs")
    op.drop_table("saisons")
    op.drop_table("competitions")
    op.drop_table("refresh_tokens")
    op.drop_constraint("fk_users_club", "users", type_="foreignkey")
    op.drop_table("clubs")
    op.drop_table("users")
