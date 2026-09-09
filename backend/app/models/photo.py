"""Médias officiels : photos de joueurs et de staff, avec versioning.

Règle de remplacement : une nouvelle photo proposta ne chasse jamais la
photo validée actuelle. Elle entre EN_ATTENTE ; l'organisateur décide ;
le pointeur `photo_actuelle_id` du sujet ne bouge qu'en cas de validation.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MotifRefusPhoto, StatutPhoto


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    sujet_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'joueur' | 'staff'
    sujet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(50))
    file_size: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    statut: Mapped[StatutPhoto] = mapped_column(String(12), default=StatutPhoto.EN_ATTENTE, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motif_refus: Mapped[MotifRefusPhoto | None] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    uploadeur = relationship("User", foreign_keys=[uploaded_by])
    reviseur = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<Photo {self.sujet_type}:{self.sujet_id} v{self.version} {self.statut}>"
