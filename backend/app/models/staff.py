"""Personnes du staff : une vraie entité, pas un champ texte du club."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoleStaff, StatutJoueur


class Staff(Base):
    __tablename__ = "staffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    nom_complet: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleStaff] = mapped_column(String(30), nullable=False)
    statut: Mapped[StatutJoueur] = mapped_column(String(12), default=StatutJoueur.ACTIF, nullable=False)
    photo_actuelle_id: Mapped[int | None] = mapped_column(ForeignKey("photos.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    club = relationship("Club", foreign_keys=[club_id])
    photo_actuelle_rel = relationship("Photo", foreign_keys=[photo_actuelle_id])

    @property
    def photo_url(self) -> str | None:
        from sqlalchemy.orm.attributes import instance_state
        ph = instance_state(self).dict.get("photo_actuelle_rel")
        if ph is None:
            return None
        from app.services.stockage_photo import url_publique
        return url_publique(ph.storage_key)

    def __repr__(self) -> str:
        return f"<Staff {self.nom_complet} ({self.role})>"
