from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutEffectif


class EffectifClub(Base):
    """État de soumission de l'effectif d'un club pour une saison."""

    __tablename__ = "effectifs_clubs"
    __table_args__ = (
        UniqueConstraint("saison_id", "club_id", name="uq_effectifs_clubs_saison_club"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saison_id: Mapped[int] = mapped_column(
        ForeignKey("saisons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statut: Mapped[StatutEffectif] = mapped_column(
        String(20), default=StatutEffectif.A_COMPLETER, nullable=False
    )
    soumis_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    soumis_par_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    traite_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    traite_par_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    motif_retour: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    saison = relationship("Saison", back_populates="effectifs")
    club = relationship("Club", back_populates="effectifs")

    def __repr__(self) -> str:
        return f"<EffectifClub saison={self.saison_id} club={self.club_id} statut={self.statut}>"
