from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import TypeCompetition


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


class SaisonClubCreate(BaseModel):
    club_id: int


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
    club_ids: list[int] = []
