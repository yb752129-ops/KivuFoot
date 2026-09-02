from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EquipeConcernee, StatutMatch


class Match(Base):
    __tablename__ = "matchs"
    __table_args__ = (
        CheckConstraint(
            "equipe_domicile_id IS NULL OR equipe_exterieur_id IS NULL OR equipe_domicile_id != equipe_exterieur_id",
            name="ck_match_equipes_differentes",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saison_id: Mapped[int] = mapped_column(ForeignKey("saisons.id", ondelete="CASCADE"), nullable=False)
    journee: Mapped[str | None] = mapped_column(String(20))
    date_heure: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stade: Mapped[str | None] = mapped_column(String(255))
    equipe_domicile_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"))
    equipe_exterieur_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"))
    score_domicile: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_exterieur: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    statut: Mapped[StatutMatch] = mapped_column(String(20), default=StatutMatch.PROGRAMME, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Forfait : ajouté suite à l'analyse Phase 0 pour ne jamais masquer un
    # forfait derrière un score 3-0 "normal" (traçabilité).
    forfait: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    forfait_equipe: Mapped[EquipeConcernee | None] = mapped_column(String(10))  # équipe forfait (qui perd 0-3)

    valide_par: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    date_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    saison = relationship("Saison", back_populates="matchs")
    equipe_domicile = relationship("Club", foreign_keys=[equipe_domicile_id])
    equipe_exterieur = relationship("Club", foreign_keys=[equipe_exterieur_id])
    evenements = relationship("EvenementMatch", back_populates="match_", cascade="all, delete-orphan")
    participations = relationship("MatchParticipation", back_populates="match_", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Match {self.id} statut={self.statut}>"


class MatchParticipation(Base):
    """
    Feuille de match : qui a joué, pour quelle équipe, titulaire ou
    remplaçant, et sur quelle plage de minutes. Table manquante dans le
    modèle original mais indispensable pour calculer titularisations et
    minutes_jouees (voir rapport Phase 0, point B). C'est aussi la
    source de vérité pour savoir pour quel club un joueur a joué un
    match donné - jamais joueurs.club_actuel_id, qui ne reflète que le
    club ACTUEL et serait faux après un transfert (décision C2 validée).
    """
    __tablename__ = "match_participations"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False)
    joueur_id: Mapped[int] = mapped_column(ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    equipe_concernee: Mapped[EquipeConcernee] = mapped_column(String(10), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)  # titulaire | remplacant
    minute_entree: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minute_sortie: Mapped[int | None] = mapped_column(Integer)  # NULL = a joué jusqu'à la fin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match_ = relationship("Match", back_populates="participations")
    joueur = relationship("Joueur")
