from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import PosteJoueur, StatutVerificationJoueur


class JoueurPublicOut(BaseModel):
    """Profil public : PAS de téléphone/email, restrictions mineurs appliquées en amont (crud)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom_complet: str
    poste: PosteJoueur | None
    club_actuel_id: int | None


class JoueurDetailOut(BaseModel):
    """Vue réservée club_manager/organisateur/admin - inclut les données personnelles."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom_complet: str
    date_naissance: date
    poste: PosteJoueur | None
    club_actuel_id: int | None
    telephone: str | None
    email: str | None
    statut_verification: StatutVerificationJoueur
    fusionne: bool
    est_mineur: bool


class JoueurCreate(BaseModel):
    nom_complet: str
    date_naissance: date
    poste: PosteJoueur | None = None
    club_actuel_id: int | None = None
    telephone: str | None = None
    email: str | None = None
    autorisation_parentale: bool | None = None

    @field_validator("date_naissance")
    @classmethod
    def date_naissance_passee(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("La date de naissance doit être dans le passé.")
        return v


class JoueurMergeRequest(BaseModel):
    joueur_maitre_id: int
    joueur_esclave_id: int

    @field_validator("joueur_esclave_id")
    @classmethod
    def ids_distincts(cls, v: int, info):
        maitre = info.data.get("joueur_maitre_id")
        if maitre is not None and v == maitre:
            raise ValueError("Impossible de fusionner un joueur avec lui-même.")
        return v


class JoueurUpdate(BaseModel):
    """C1 : téléphone / e-mail seulement. Le reste passe par une proposition."""

    telephone: str | None = None
    email: str | None = None

    @field_validator("telephone", "email")
    @classmethod
    def champ_optionnel(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class ModificationProposeeCreate(BaseModel):
    champ: str
    nouvelle_valeur: str


class ModificationProposeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    joueur_id: int
    champ: str
    ancienne_valeur: str | None
    nouvelle_valeur: str
    statut: str
