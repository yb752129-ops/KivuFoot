from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentOfficiel(Base):
    __tablename__ = "documents_officiels"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_document: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), index=True)
    saison_id: Mapped[int | None] = mapped_column(ForeignKey("saisons.id", ondelete="RESTRICT"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="genere", index=True)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    empreinte_source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    message_erreur: Mapped[str | None] = mapped_column(Text)
    genere_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    publie_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    remplace_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents_officiels.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    remplacant = relationship("DocumentOfficiel", remote_side=[id])
    competition = relationship("Competition")
    saison = relationship("Saison")
