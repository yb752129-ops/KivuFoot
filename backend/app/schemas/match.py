from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import EquipeConcernee, PeriodeMatch, StatutMatch, StatutParticipation


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    saison_id: int
    journee: str | None
    date_heure: datetime
    stade: str | None
    equipe_domicile_id: int | None
    equipe_exterieur_id: int | None
    score_domicile: int
    score_exterieur: int
    statut: StatutMatch
    started_at: datetime | None = None
    ended_at: datetime | None = None
    periode: PeriodeMatch | None = None
    periode_started_at: datetime | None = None
    paused_at: datetime | None = None
    forfait: bool
    forfait_equipe: EquipeConcernee | None
    locked: bool


class MatchCreate(BaseModel):
    saison_id: int
    journee: str | None = None
    date_heure: datetime
    stade: str | None = None
    equipe_domicile_id: int
    equipe_exterieur_id: int

    @field_validator("equipe_exterieur_id")
    @classmethod
    def equipes_distinctes(cls, v: int, info):
        dom = info.data.get("equipe_domicile_id")
        if dom is not None and v == dom:
            raise ValueError("Une équipe ne peut pas jouer contre elle-même.")
        return v


class MatchStatutUpdate(BaseModel):
    statut: StatutMatch
    forfait: bool = False
    forfait_equipe: EquipeConcernee | None = None


class ParticipationCreate(BaseModel):
    joueur_id: int
    club_id: int
    equipe_concernee: EquipeConcernee
    statut: StatutParticipation
    minute_entree: int = 0
    minute_sortie: int | None = None


class ParticipationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    joueur_id: int
    club_id: int
    equipe_concernee: EquipeConcernee
    statut: StatutParticipation
    minute_entree: int
    minute_sortie: int | None
