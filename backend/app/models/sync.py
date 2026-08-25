from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutConflit, StatutSync, TypeSync


class StockageSynchronisation(Base):
    """
    File d'attente de synchronisation offline-first.

    `temp_id` (ajouté suite au rapport Phase 0, point B) est généré côté
    client (UUID v4) au moment de la saisie locale. La contrainte unique
    (utilisateur_id, temp_id) garantit l'IDEMPOTENCE : si le push réseau
    échoue et que le client retente, le serveur reconnaît le doublon et
    ne recrée pas l'événement. C'est un point critique pour la fiabilité
    des données en contexte de connexion instable.
    """
    __tablename__ = "stockage_synchronisation"
    __table_args__ = (
        UniqueConstraint("utilisateur_id", "temp_id", name="uq_sync_utilisateur_temp_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    temp_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    type: Mapped[TypeSync] = mapped_column(String(50), nullable=False)
    donnees: Mapped[dict] = mapped_column(JSONB, nullable=False)
    statut: Mapped[StatutSync] = mapped_column(String(20), default=StatutSync.LOCAL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    utilisateur = relationship("User")


class ConflitSynchronisation(Base):
    """
    Table absente du modèle §4 original bien que mentionnée en §6.3
    (rapport Phase 0, point B). Conserve les deux versions en conflit
    jusqu'à arbitrage par l'organisateur.
    """
    __tablename__ = "conflits_synchronisation"

    id: Mapped[int] = mapped_column(primary_key=True)
    evenement_id: Mapped[int | None] = mapped_column(ForeignKey("evenements_match.id", ondelete="CASCADE"))
    version_a: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version_b: Mapped[dict] = mapped_column(JSONB, nullable=False)
    utilisateur_a_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    utilisateur_b_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    statut: Mapped[StatutConflit] = mapped_column(String(20), default=StatutConflit.EN_ATTENTE, nullable=False)
    resolu_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolution: Mapped[dict | None] = mapped_column(JSONB)
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evenement = relationship("EvenementMatch")
