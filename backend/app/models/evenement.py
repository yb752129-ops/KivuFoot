import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    EquipeConcernee,
    ResultatPenalty,
    StatutValidationEvenement,
    TypeEvenement,
)


class EvenementMatch(Base):
    """
    Corrections apportées suite au rapport Phase 0 (point A1) :

    - `joueur_secondaire_id` remplace l'ambiguïté joueur_assist_id /
      joueur_sortant/entrant : sa sémantique dépend de `type`
        * passe_decisive    -> joueur_id = buteur, joueur_secondaire_id = passeur
        * remplacement      -> joueur_id = sortant, joueur_secondaire_id = entrant
        * autres types      -> joueur_secondaire_id = NULL
    - `resultat` ajouté pour les penalties (marque / rate). RÈGLE STRICTE :
      un penalty marqué N'EST JAMAIS dupliqué en un second événement
      'but' - le service de calcul de score/stats traite
      type='penalty' + resultat='marque' comme un but à part entière.
      Voir services/calcul_stats.py.
    - `but_contre_son_camp` ajouté comme type dédié (absent de la spec
      originale) pour ne pas fausser les statistiques individuelles du
      buteur ni la logique d'attribution du but.
    - `temp_id` (UUID généré côté client) rend la synchronisation
      idempotente : un retry réseau ne peut pas dupliquer un événement.
    - `conflit` matérialise le flag mentionné en §6.3 mais absent du
      schéma original.
    - `locked` empêche toute modification d'un événement déjà validé
      (le principe "donnée validée non modifiable" ne s'appliquait
      jusqu'ici qu'au niveau match - point A3 du rapport).
    """
    __tablename__ = "evenements_match"
    __table_args__ = (
        CheckConstraint("minute >= 0", name="ck_evenement_minute_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TypeEvenement] = mapped_column(String(30), nullable=False)

    joueur_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="SET NULL"))
    joueur_secondaire_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="SET NULL"))
    resultat: Mapped[ResultatPenalty | None] = mapped_column(String(10))  # uniquement pour type='penalty'

    equipe_concernee: Mapped[EquipeConcernee] = mapped_column(String(10), nullable=False)

    statut_validation: Mapped[StatutValidationEvenement] = mapped_column(
        String(20), default=StatutValidationEvenement.EN_ATTENTE, nullable=False, index=True
    )
    valide_par: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    date_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commentaire_rejet: Mapped[str | None] = mapped_column(String)

    conflit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[str] = mapped_column(String(50), default="collecteur_mobile", nullable=False)
    temp_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match_ = relationship("Match", back_populates="evenements")
    joueur = relationship("Joueur", foreign_keys=[joueur_id])
    joueur_secondaire = relationship("Joueur", foreign_keys=[joueur_secondaire_id])

    def __repr__(self) -> str:
        return f"<Evenement {self.type} match={self.match_id} statut={self.statut_validation}>"
