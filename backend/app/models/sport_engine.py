"""Modèles additifs du moteur sportif.

Ces tables ne remplacent aucune source historique existante. Elles portent
les versions de règlement, les snapshots d'effectifs, les contrôles, les
anomalies et les décisions dérivées ou humaines. Les faits de match restent
dans EvenementMatch et MatchParticipation.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReglementVersion(Base):
    __tablename__ = "reglements_versions"
    __table_args__ = (
        UniqueConstraint("saison_id", "version", name="uq_reglement_saison_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    saison_id: Mapped[int] = mapped_column(
        ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[str] = mapped_column(String(32), default="brouillon", nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="1", nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_officielle: Mapped[str | None] = mapped_column(Text)
    reference_decision: Mapped[str | None] = mapped_column(String(255))
    date_effet: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    active_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    competition = relationship("Competition")
    saison = relationship("Saison")
    createur = relationship("User", foreign_keys=[cree_par_id])
    activateur = relationship("User", foreign_keys=[active_par_id])


class EffectifVersion(Base):
    __tablename__ = "effectifs_versions"
    __table_args__ = (
        UniqueConstraint("saison_id", "club_id", "version", name="uq_effectif_version_saison_club"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saison_id: Mapped[int] = mapped_column(
        ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[str] = mapped_column(String(32), default="brouillon", nullable=False, index=True)
    motif: Mapped[str | None] = mapped_column(Text)
    soumis_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    valide_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    soumis_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valide_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_effet: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    joueurs = relationship("EffectifVersionJoueur", back_populates="effectif", cascade="all, delete-orphan")
    saison = relationship("Saison")
    club = relationship("Club")


class EffectifVersionJoueur(Base):
    __tablename__ = "effectifs_versions_joueurs"
    __table_args__ = (
        UniqueConstraint("effectif_version_id", "joueur_id", name="uq_effectif_version_joueur"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    effectif_version_id: Mapped[int] = mapped_column(
        ForeignKey("effectifs_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joueur_id: Mapped[int] = mapped_column(
        ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    motif: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    effectif = relationship("EffectifVersion", back_populates="joueurs")
    joueur = relationship("Joueur")


class SanctionDisciplinaire(Base):
    __tablename__ = "sanctions_disciplinaires"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    saison_id: Mapped[int] = mapped_column(
        ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    joueur_id: Mapped[int] = mapped_column(
        ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reglement_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("reglements_versions.id", ondelete="RESTRICT"), index=True
    )
    evenement_declencheur_id: Mapped[int | None] = mapped_column(
        ForeignKey("evenements_match.id", ondelete="RESTRICT"), index=True
    )
    type_motif: Mapped[str] = mapped_column(String(50), nullable=False)
    statut: Mapped[str] = mapped_column(String(32), default="calculee", nullable=False, index=True)
    nombre_matchs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matchs_restants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    explication: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    empreinte_source: Mapped[str | None] = mapped_column(String(64), index=True)
    date_effet: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    matchs = relationship("SanctionMatch", back_populates="sanction", cascade="all, delete-orphan")
    joueur = relationship("Joueur")
    evenement_declencheur = relationship("EvenementMatch")
    reglement = relationship("ReglementVersion")


class SanctionMatch(Base):
    __tablename__ = "sanctions_matchs"
    __table_args__ = (
        UniqueConstraint("sanction_id", "match_id", name="uq_sanction_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sanction_id: Mapped[int] = mapped_column(
        ForeignKey("sanctions_disciplinaires.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ordre: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), default="a_servir", nullable=False)

    sanction = relationship("SanctionDisciplinaire", back_populates="matchs")
    match = relationship("Match")


class DecisionSportive(Base):
    __tablename__ = "decisions_sportives"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), index=True)
    saison_id: Mapped[int | None] = mapped_column(ForeignKey("saisons.id", ondelete="RESTRICT"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matchs.id", ondelete="RESTRICT"), index=True)
    joueur_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="RESTRICT"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), index=True)
    sanction_id: Mapped[int | None] = mapped_column(ForeignKey("sanctions_disciplinaires.id", ondelete="RESTRICT"), index=True)
    anomalie_id: Mapped[int | None] = mapped_column(ForeignKey("anomalies_historiques.id", ondelete="RESTRICT"), index=True)
    type_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), default="confirmee", nullable=False)
    motif: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    decide_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    decideur = relationship("User")


class ControleValidationMatch(Base):
    __tablename__ = "controles_validation_matchs"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matchs.id", ondelete="RESTRICT"), nullable=False, index=True)
    reglement_version_id: Mapped[int | None] = mapped_column(ForeignKey("reglements_versions.id", ondelete="RESTRICT"), index=True)
    resultat: Mapped[str] = mapped_column(String(20), nullable=False)
    empreinte_source: Mapped[str | None] = mapped_column(String(64), index=True)
    controles: Mapped[dict] = mapped_column(JSONB, nullable=False)
    execute_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    match = relationship("Match")
    reglement = relationship("ReglementVersion")


class AnomalieHistorique(Base):
    __tablename__ = "anomalies_historiques"
    __table_args__ = (
        UniqueConstraint("saison_id", "match_id", "type_anomalie", "empreinte", name="uq_anomalie_observation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saison_id: Mapped[int] = mapped_column(ForeignKey("saisons.id", ondelete="RESTRICT"), nullable=False, index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matchs.id", ondelete="RESTRICT"), index=True)
    joueur_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="RESTRICT"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), index=True)
    type_anomalie: Mapped[str] = mapped_column(String(64), nullable=False)
    severite: Mapped[str] = mapped_column(String(20), default="attention", nullable=False)
    statut: Mapped[str] = mapped_column(String(40), default="a_examiner", nullable=False, index=True)
    observation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    empreinte: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str | None] = mapped_column(Text)
    decide_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decide_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    match = relationship("Match")
    joueur = relationship("Joueur")
    club = relationship("Club")
    decideur = relationship("User")
