import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.enums import (
    EquipeConcernee,
    ResultatPenalty,
    StatutValidationEvenement,
    TypeEvenement,
)

# Champs obligatoires par type d'événement (§3.4 de la spécification,
# corrigé Phase 0 : ajout de but_contre_son_camp, resultat pour penalty).
CHAMPS_REQUIS_PAR_TYPE: dict[TypeEvenement, set[str]] = {
    TypeEvenement.BUT: {"joueur_id"},
    TypeEvenement.BUT_CONTRE_SON_CAMP: {"joueur_id"},
    TypeEvenement.PASSE_DECISIVE: {"joueur_id", "joueur_secondaire_id"},
    TypeEvenement.CARTON_JAUNE: {"joueur_id"},
    TypeEvenement.CARTON_ROUGE: {"joueur_id"},
    TypeEvenement.REMPLACEMENT: {"joueur_id", "joueur_secondaire_id"},
    TypeEvenement.PENALTY: {"joueur_id", "resultat"},
}


class EvenementCreate(BaseModel):
    """
    Saisie d'un événement par le collecteur (ou reçu via /sync/push).
    `temp_id` est obligatoire pour garantir l'idempotence de la
    synchronisation offline-first.
    """
    temp_id: uuid.UUID
    minute: int
    minute_additionnelle: int = 0
    periode: str | None = None
    type: TypeEvenement
    joueur_id: int | None = None
    joueur_secondaire_id: int | None = None
    resultat: ResultatPenalty | None = None
    equipe_concernee: EquipeConcernee

    @field_validator("minute")
    @classmethod
    def minute_valide(cls, v: int) -> int:
        if v < 0:
            raise ValueError("La minute ne peut pas être négative.")
        if v > 130:
            raise ValueError("Minute improbable (> 130) - vérifier la saisie.")
        return v

    @field_validator("minute_additionnelle")
    @classmethod
    def additionnelle_valide(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Le temps additionnel ne peut pas être négatif.")
        if v > 20:
            raise ValueError("Temps additionnel improbable (> 20).")
        return v

    @field_validator("periode")
    @classmethod
    def periode_valide(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if v not in ("1", "2"):
            raise ValueError("La période d'un événement est 1 ou 2.")
        return v

    @model_validator(mode="after")
    def champs_requis_selon_type(self):
        requis = CHAMPS_REQUIS_PAR_TYPE.get(self.type, set())
        for champ in requis:
            if getattr(self, champ, None) is None:
                raise ValueError(f"Le champ '{champ}' est obligatoire pour un événement de type '{self.type}'.")
        if self.type != TypeEvenement.PENALTY and self.resultat is not None:
            raise ValueError("Le champ 'resultat' n'est utilisé que pour les penalties.")
        return self


class EvenementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    minute: int
    minute_additionnelle: int = 0
    periode: str | None = None
    type: TypeEvenement
    joueur_id: int | None
    joueur_secondaire_id: int | None
    resultat: ResultatPenalty | None
    equipe_concernee: EquipeConcernee
    statut_validation: StatutValidationEvenement
    conflit: bool
    locked: bool
    commentaire_rejet: str | None
    created_at: datetime


class ValidationRejetRequest(BaseModel):
    commentaire: str

    @field_validator("commentaire")
    @classmethod
    def commentaire_obligatoire(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Un commentaire est obligatoire pour rejeter un événement.")
        return v.strip()
