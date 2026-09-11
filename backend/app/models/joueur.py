from datetime import date, datetime

from sqlalchemy import Integer, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PosteJoueur, StatutJoueur, StatutVerificationJoueur


class Joueur(Base):
    __tablename__ = "joueurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom_complet: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date_naissance: Mapped[date] = mapped_column(Date, nullable=False)
    poste: Mapped[PosteJoueur | None] = mapped_column(String(50))
    numero: Mapped[int | None] = mapped_column(Integer)  # numéro de maillot : optionnel, contextuel, jamais identifiant
    club_actuel_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"))
    statut: Mapped[StatutJoueur] = mapped_column(String(12), default=StatutJoueur.ACTIF, nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))

    # --- Champs ajoutés suite à l'analyse Phase 0 (mentionnés dans le texte
    # de la spécification §7 et §10 mais absents du modèle de données §4) ---
    statut_verification: Mapped[StatutVerificationJoueur] = mapped_column(
        String(30), default=StatutVerificationJoueur.VERIFIE, nullable=False
    )
    fusionne: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fusionne_vers_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="SET NULL"))
    autorisation_parentale: Mapped[bool | None] = mapped_column(Boolean)  # requis si mineur, renseigné par club_manager
    anonymise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    photo_actuelle_id: Mapped[int | None] = mapped_column(ForeignKey("photos.id", ondelete="SET NULL"))

    photo_actuelle_rel = relationship("Photo", foreign_keys=[photo_actuelle_id])
    club_actuel = relationship("Club", back_populates="joueurs", foreign_keys=[club_actuel_id])
    consentements = relationship("Consentement", back_populates="joueur", cascade="all, delete-orphan")

    @property
    def photo_url(self) -> str | None:
        """Uniquement la photo VALIDÉE courante ; jamais une photo en attente."""
        from sqlalchemy.orm.attributes import instance_state
        ph = instance_state(self).dict.get("photo_actuelle_rel")
        if ph is None:
            return None
        from app.services.stockage_photo import url_publique
        return url_publique(ph.storage_key)

    @property
    def est_mineur(self) -> bool:
        today = date.today()
        age = today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )
        return age < 18

    def __repr__(self) -> str:
        return f"<Joueur {self.nom_complet}>"


class JoueurModificationProposee(Base):
    """
    Workflow de proposition/validation pour les modifications de joueur
    par un club_manager (décision C1 validée : le club_manager "propose"
    des modifications sur les champs sensibles, l'admin/organisateur
    approuve ou rejette). Les champs non sensibles (téléphone, email)
    peuvent être modifiés directement sans passer par ce workflow -
    voir crud/joueurs.py.
    """
    __tablename__ = "joueurs_modifications_proposees"

    id: Mapped[int] = mapped_column(primary_key=True)
    joueur_id: Mapped[int] = mapped_column(ForeignKey("joueurs.id", ondelete="CASCADE"), nullable=False)
    proposee_par_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    champ: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: 'club_actuel_id', 'date_naissance'
    ancienne_valeur: Mapped[str | None] = mapped_column(String(255))
    nouvelle_valeur: Mapped[str] = mapped_column(String(255), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), default="en_attente", nullable=False)
    traitee_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    date_traitement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commentaire: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    joueur = relationship("Joueur")
