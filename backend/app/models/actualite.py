"""Contenu éditorial officiel de KivuFoot.

Les actualités complètent les données sportives sans les recopier ni les
remplacer. Les publications sont toujours rattachées à l'auteur qui les a
créées et restent archivables plutôt que supprimées physiquement.
"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CategorieActualite, StatutActualite


class Actualite(Base):
    __tablename__ = "actualites"
    __table_args__ = (
        CheckConstraint(
            "statut IN ('brouillon','publie','archive')",
            name="ck_actualites_statut",
        ),
        CheckConstraint(
            "categorie IN ('annonce','match_competition','retour_journee','homme_du_match','performance','photo_moment','fair_play','information_importante')",
            name="ck_actualites_categorie",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(180), nullable=False)
    categorie: Mapped[CategorieActualite] = mapped_column(String(40), nullable=False, index=True)
    texte: Mapped[str] = mapped_column(Text, nullable=False)
    statut: Mapped[StatutActualite] = mapped_column(
        String(20), default=StatutActualite.BROUILLON, nullable=False, index=True
    )
    telechargement_autorise: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Priorité éditoriale : les brouillons et archives restent toujours hors du flux public.
    mise_en_avant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    auteur_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id", ondelete="SET NULL"), index=True)
    saison_id: Mapped[int | None] = mapped_column(ForeignKey("saisons.id", ondelete="SET NULL"), index=True)
    journee: Mapped[str | None] = mapped_column(String(30))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matchs.id", ondelete="SET NULL"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"), index=True)
    joueur_id: Mapped[int | None] = mapped_column(ForeignKey("joueurs.id", ondelete="SET NULL"), index=True)

    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_modification: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    date_publication: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    auteur = relationship("User")
    competition = relationship("Competition")
    saison = relationship("Saison")
    match = relationship("Match")
    club = relationship("Club")
    joueur = relationship("Joueur")
    images = relationship(
        "ActualiteImage",
        back_populates="actualite",
        cascade="all, delete-orphan",
        order_by="ActualiteImage.ordre, ActualiteImage.id",
    )
    likes = relationship("ActualiteLike", back_populates="actualite", cascade="all, delete-orphan")
    lectures = relationship("ActualiteLecture", back_populates="actualite", cascade="all, delete-orphan")


class ActualiteImage(Base):
    __tablename__ = "actualite_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    actualite_id: Mapped[int] = mapped_column(ForeignKey("actualites.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(50))
    file_size: Mapped[int | None] = mapped_column(Integer)
    ordre: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    principale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actualite = relationship("Actualite", back_populates="images")
    uploadeur = relationship("User")


class ActualiteLike(Base):
    __tablename__ = "actualite_likes"
    __table_args__ = (
        UniqueConstraint("actualite_id", "token_hash", name="uq_actualite_likes_actualite_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actualite_id: Mapped[int] = mapped_column(ForeignKey("actualites.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actualite = relationship("Actualite", back_populates="likes")


class ActualiteLecture(Base):
    __tablename__ = "actualite_lectures"
    __table_args__ = (
        UniqueConstraint("actualite_id", "token_hash", name="uq_actualite_lectures_actualite_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actualite_id: Mapped[int] = mapped_column(ForeignKey("actualites.id", ondelete="CASCADE"), nullable=False, index=True)
    # Le jeton anonyme est haché, comme pour les likes : aucune valeur client brute n'est persistée.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    date_lecture: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actualite = relationship("Actualite", back_populates="lectures")


class HommeMatch(Base):
    __tablename__ = "hommes_match"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_hommes_match_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matchs.id", ondelete="CASCADE"), nullable=False, index=True)
    joueur_id: Mapped[int] = mapped_column(ForeignKey("joueurs.id", ondelete="RESTRICT"), nullable=False, index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False)
    designe_par_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    designe_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    match = relationship("Match")
    joueur = relationship("Joueur")
    club = relationship("Club")
    designeur = relationship("User")
