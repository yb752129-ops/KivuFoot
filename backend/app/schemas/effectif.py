from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import StatutEffectif


class EffectifClubOut(BaseModel):
    saison_id: int
    club_id: int
    club_nom: str
    statut: StatutEffectif
    total_joueurs: int
    joueurs_sans_photo: int
    soumis_at: datetime | None = None
    soumis_par_id: int | None = None
    traite_at: datetime | None = None
    traite_par_id: int | None = None
    motif_retour: str | None = None
    peut_soumettre: bool


class EffectifRetour(BaseModel):
    motif: str = Field(min_length=10, max_length=500)


class ControleEffectifMatchOut(BaseModel):
    match_id: int
    saison_id: int
    domicile: EffectifClubOut
    exterieur: EffectifClubOut
    validation_requise: bool
    blocage_automatique: bool = False
