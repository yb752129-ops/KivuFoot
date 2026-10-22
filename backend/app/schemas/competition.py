from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import GroupePoule, StatutEquipeEdition, TypeCompetition


class ClubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    stade: str | None
    ville: str
    logo_url: str | None
    coach_nom: str | None = None


class ClubCreate(BaseModel):
    nom: str
    stade: str | None = None
    ville: str
    logo_url: str | None = None

    @field_validator("nom", "ville")
    @classmethod
    def champ_non_vide(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Ce champ est obligatoire.")
        return str(v).strip()

    @field_validator("stade")
    @classmethod
    def stade_propre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class ClubUpdate(BaseModel):
    nom: str | None = None
    stade: str | None = None
    ville: str | None = None
    logo_url: str | None = None

    @field_validator("nom", "ville")
    @classmethod
    def champ_non_vide(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not str(v).strip():
            raise ValueError("Ce champ est obligatoire.")
        return str(v).strip()

    @field_validator("stade", "logo_url")
    @classmethod
    def champ_optionnel(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class SaisonClubOut(ClubOut):
    """Projection publique d'une équipe inscrite dans une édition.

    Le motif, l'auteur et les détails de l'audit ne font volontairement pas
    partie de ce schéma public.
    """

    saison_id: int
    club_id: int
    groupe: GroupePoule | None = None
    statut: StatutEquipeEdition = StatutEquipeEdition.ACTIF


class SaisonClubGestionOut(SaisonClubOut):
    """Projection réservée à l'administration et à l'organisation."""

    statut_at: datetime | None = None
    statut_motif: str | None = None
    statut_modifie_par_id: int | None = None


class SaisonClubCreate(BaseModel):
    club_id: int
    groupe: GroupePoule | None = None

    @field_validator("groupe", mode="before")
    @classmethod
    def groupe_normalise(cls, v):
        if v is None:
            return None
        valeur = str(v).strip().upper()
        return valeur or None


class SaisonClubGroupeUpdate(BaseModel):
    groupe: GroupePoule | None = None

    @field_validator("groupe", mode="before")
    @classmethod
    def groupe_normalise(cls, v):
        if v is None:
            return None
        valeur = str(v).strip().upper()
        return valeur or None


class SaisonClubStatutUpdate(BaseModel):
    statut: StatutEquipeEdition | None = None
    motif: str | None = Field(default=None, max_length=500)

    @field_validator("motif")
    @classmethod
    def motif_normalise(cls, v: str | None) -> str | None:
        if v is None:
            return None
        valeur = v.strip()
        return valeur or None


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    type: TypeCompetition
    saison_label: str | None
    est_active: bool
    est_demo: bool


class CompetitionCreate(BaseModel):
    nom: str
    type: TypeCompetition
    saison_label: str | None = None
    est_demo: bool = False

    @field_validator("nom")
    @classmethod
    def nom_non_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom de la compétition ne peut pas être vide.")
        return v.strip()


class SaisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    nom: str | None
    date_debut: date | None
    date_fin: date | None


class SaisonCreate(BaseModel):
    competition_id: int
    nom: str | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    club_ids: list[int] = Field(default_factory=list)
