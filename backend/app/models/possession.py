"""Modèle séparé de possession, fondé uniquement sur le temps observé.

La possession n'est volontairement pas un événement sportif : les intervalles
sont append-only, les opérations sont idempotentes et chaque changement est
traçable. Une seconde de contrôle incertaine est conservée en PAUSE, jamais
dérivée des passes, tirs ou autres événements du match.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    EtatPossession,
    MethodePossession,
    ProtocolePossession,
    StatutPossession,
)


class PossessionMatch(Base):
    __tablename__ = "possessions_matchs"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_possessions_matchs_match_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False, index=True)
    equipe_a_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False)
    equipe_b_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False)

    # Méthode et protocole sont stockés sur chaque capture, afin qu'une
    # future version ne puisse pas être confondue avec V1.
    methode: Mapped[MethodePossession] = mapped_column(String(30), nullable=False, default=MethodePossession.TIME_BASED)
    protocole: Mapped[ProtocolePossession] = mapped_column(
        String(60), nullable=False, default=ProtocolePossession.KIVUFOOT_POSSESSION_V1
    )
    etat_courant: Mapped[EtatPossession] = mapped_column(
        String(20), nullable=False, default=EtatPossession.NOT_STARTED
    )
    # Vrai pendant l'intervalle entre mi-temps et reprise : ce temps de
    # match suspendu ne doit pas devenir artificiellement du non-attribué.
    pause_hors_jeu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    statut: Mapped[StatutPossession] = mapped_column(
        String(20), nullable=False, default=StatutPossession.PROVISOIRE
    )

    # Compteurs persistés en millisecondes : pas d'arrondi cumulatif.
    temps_a_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    temps_b_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    temps_non_attribue_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    nombre_changements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nombre_sequences_a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nombre_sequences_b: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    collecteur_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    valide_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    officialisee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derniere_transition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Une capture issue d'un forfait, d'une interruption non définie ou d'un
    # autre format non couvert par V1 ne devient jamais visible par accident.
    eligible_public: Mapped[bool] = mapped_column(nullable=False, default=True)
    motif_exclusion_public: Mapped[str | None] = mapped_column(String(255))

    match = relationship("Match")
    equipe_a = relationship("Club", foreign_keys=[equipe_a_id])
    equipe_b = relationship("Club", foreign_keys=[equipe_b_id])
    collecteur = relationship("User", foreign_keys=[collecteur_id])
    valide_par = relationship("User", foreign_keys=[valide_par_id])
    intervalles = relationship(
        "PossessionIntervalle",
        back_populates="possession",
        cascade="all, delete-orphan",
        order_by="PossessionIntervalle.id",
    )
    operations = relationship(
        "PossessionOperation",
        back_populates="possession",
        cascade="all, delete-orphan",
        order_by="PossessionOperation.id",
    )
    corrections = relationship(
        "PossessionCorrection",
        back_populates="possession",
        cascade="all, delete-orphan",
        order_by="PossessionCorrection.id",
    )

    @property
    def temps_a(self) -> float:
        return (self.temps_a_ms or 0) / 1000

    @property
    def temps_b(self) -> float:
        return (self.temps_b_ms or 0) / 1000

    @property
    def temps_non_attribue(self) -> float:
        return (self.temps_non_attribue_ms or 0) / 1000


class PossessionIntervalle(Base):
    __tablename__ = "possession_intervalles"

    id: Mapped[int] = mapped_column(primary_key=True)
    possession_id: Mapped[int] = mapped_column(
        ForeignKey("possessions_matchs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    etat: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    debut_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duree_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    periode: Mapped[str | None] = mapped_column(String(12))
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    possession = relationship("PossessionMatch", back_populates="intervalles")
    cree_par = relationship("User", foreign_keys=[cree_par_id])


class PossessionCorrection(Base):
    """Anciennes et nouvelles valeurs d'une correction organisateur."""

    __tablename__ = "possession_corrections"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_possession_corrections_operation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    possession_id: Mapped[int] = mapped_column(
        ForeignKey("possessions_matchs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    intervalle_id: Mapped[int] = mapped_column(
        ForeignKey("possession_intervalles.id", ondelete="RESTRICT"), nullable=False
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ancien_etat: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    ancien_debut_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ancien_fin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ancien_duree_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nouvel_etat: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    nouveau_debut_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nouveau_fin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nouvelle_duree_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    motif: Mapped[str] = mapped_column(Text, nullable=False)
    corrige_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    possession = relationship("PossessionMatch", back_populates="corrections")
    intervalle = relationship("PossessionIntervalle")
    corrige_par = relationship("User", foreign_keys=[corrige_par_id])


class PossessionOperation(Base):
    """Journal technique idempotent des commandes reçues du mobile/web."""

    __tablename__ = "possession_operations"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_possession_operations_operation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    possession_id: Mapped[int] = mapped_column(
        ForeignKey("possessions_matchs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    etat_demande: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    etat_avant: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    etat_apres: Mapped[EtatPossession] = mapped_column(String(20), nullable=False)
    appliquee_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    correction: Mapped[bool] = mapped_column(nullable=False, default=False)

    possession = relationship("PossessionMatch", back_populates="operations")
    cree_par = relationship("User", foreign_keys=[cree_par_id])
