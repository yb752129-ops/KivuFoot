"""Registre indépendant des distinctions : aucune relation aux données sportives."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Certificat(Base):
    __tablename__ = 'certificats_distinction'
    __table_args__ = (CheckConstraint("statut IN ('actif','annule')", name='ck_certificats_distinction_statut'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    laureat: Mapped[str] = mapped_column(String(200), nullable=False)
    distinction: Mapped[str] = mapped_column(String(200), nullable=False)
    equipe: Mapped[str] = mapped_column(String(200), nullable=False)
    tournoi: Mapped[str] = mapped_column(String(250), nullable=False)
    organisateur: Mapped[str] = mapped_column(String(200), nullable=False)
    statut: Mapped[str] = mapped_column(String(10), nullable=False, default='actif')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
