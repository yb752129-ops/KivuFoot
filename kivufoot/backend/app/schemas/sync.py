import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatutSync, TypeSync
from app.schemas.evenement import EvenementCreate


class SyncPushItem(BaseModel):
    type: TypeSync
    evenement: EvenementCreate | None = None  # rempli si type == 'evenement'
    match_id: int | None = None


class SyncPushRequest(BaseModel):
    items: list[SyncPushItem]


class SyncPushResultItem(BaseModel):
    temp_id: uuid.UUID | None
    statut: StatutSync
    evenement_id: int | None = None
    erreur: str | None = None


class SyncPushResponse(BaseModel):
    resultats: list[SyncPushResultItem]


class SyncPullResponse(BaseModel):
    matchs_maj: list[dict]
    evenements_maj: list[dict]
    derniere_sync: datetime


class ClassementLigne(BaseModel):
    club_id: int
    club_nom: str
    matchs_joues: int
    victoires: int
    nuls: int
    defaites: int
    buts_marques: int
    buts_encaisses: int
    difference_buts: int
    points: int


class TopStatLigne(BaseModel):
    joueur_id: int
    joueur_nom: str
    club_nom: str | None
    valeur: int
