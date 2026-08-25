from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stade: Mapped[str | None] = mapped_column(String(255))
    ville: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    joueurs = relationship("Joueur", back_populates="club_actuel", foreign_keys="Joueur.club_actuel_id")
    managers = relationship("User", back_populates="club")

    def __repr__(self) -> str:
        return f"<Club {self.nom}>"
