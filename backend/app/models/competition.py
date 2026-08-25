from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TypeCompetition

# Marqueur utilisé pour toute compétition de démonstration - jamais mélangée
# aux données réelles (règle non négociable de la spécification).
DEMO_PREFIX = "DEMO - "


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TypeCompetition] = mapped_column(String(50), nullable=False)
    saison_label: Mapped[str | None] = mapped_column("saison", String(50))
    est_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    est_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    saisons = relationship("Saison", back_populates="competition", cascade="all, delete-orphan")
    organisateurs = relationship("OrganisateurCompetition", back_populates="competition")

    def __repr__(self) -> str:
        return f"<Competition {self.nom}>"


class Saison(Base):
    __tablename__ = "saisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str | None] = mapped_column(String(100))
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competition = relationship("Competition", back_populates="saisons")
    clubs = relationship("SaisonClub", back_populates="saison", cascade="all, delete-orphan")
    matchs = relationship("Match", back_populates="saison")


class SaisonClub(Base):
    __tablename__ = "saison_clubs"

    saison_id: Mapped[int] = mapped_column(ForeignKey("saisons.id", ondelete="CASCADE"), primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True)

    saison = relationship("Saison", back_populates="clubs")
    club = relationship("Club")


class OrganisateurCompetition(Base):
    """
    Table de liaison indispensable pour appliquer la règle RBAC :
    "un organisateur ne peut valider que les matchs de ses compétitions"
    (absente du modèle de données original - voir rapport Phase 0, point B).
    """
    __tablename__ = "organisateur_competitions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organisateur = relationship("User", back_populates="competitions_organisees")
    competition = relationship("Competition", back_populates="organisateurs")
