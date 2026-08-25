from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TypeConsentement


class Consentement(Base):
    """
    Table formalisée à partir du texte §10.1 (absente du modèle §4
    original - rapport Phase 0, point B). Nécessaire pour la conformité
    RGPD / lois locales sur la collecte de données personnelles.
    """
    __tablename__ = "consentements"

    id: Mapped[int] = mapped_column(primary_key=True)
    joueur_id: Mapped[int] = mapped_column(ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[TypeConsentement] = mapped_column(String(20), nullable=False)
    valide: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date_consentement: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # club | collecteur | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    joueur = relationship("Joueur", back_populates="consentements")


class StatistiqueJoueur(Base):
    """
    Vue calculée / matérialisée. Clé primaire corrigée en composite
    (joueur_id, competition_id, saison_id) - la clé simple sur
    joueur_id de la spec originale empêchait d'avoir des statistiques
    distinctes par compétition ET par saison pour un même joueur
    (rapport Phase 0, point A4).

    Recalculée par services/calcul_stats.py à chaque validation
    d'événement, à partir de evenements_match + match_participations
    UNIQUEMENT (jamais à partir de joueurs.club_actuel_id - voir
    modèle Match/MatchParticipation).
    """
    __tablename__ = "statistiques_joueurs"

    joueur_id: Mapped[int] = mapped_column(ForeignKey("joueurs.id", ondelete="CASCADE"), primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True)
    saison_id: Mapped[int] = mapped_column(ForeignKey("saisons.id", ondelete="CASCADE"), primary_key=True)

    matchs_joues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    titularisations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passes_decisives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cartons_jaunes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cartons_rouges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minutes_jouees: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    joueur = relationship("Joueur")
    competition = relationship("Competition")
    saison = relationship("Saison")
