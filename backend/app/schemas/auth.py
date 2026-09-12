from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import RoleUtilisateur


class LoginRequest(BaseModel):
    email: EmailStr
    mot_de_passe: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: RoleUtilisateur
    nom_complet: str | None
    club_id: int | None
    est_actif: bool


class UserCreate(BaseModel):
    email: EmailStr
    mot_de_passe: str
    role: RoleUtilisateur
    nom_complet: str | None = None
    club_id: int | None = None


class RegisterRequest(BaseModel):
    nom_complet: str = Field(min_length=2, max_length=255)
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=72)

    @field_validator("nom_complet")
    @classmethod
    def nom_non_vide(cls, v: str) -> str:
        nom = v.strip()
        if len(nom) < 2:
            raise ValueError("Le nom complet est trop court.")
        return nom


# ---------------------------------------------------------------------------
# Comptes réels : activation, changement de mot de passe, gestion admin.
# Aucun schéma ne transporte jamais un mot de passe existant vers le client :
# le hash reste en base, les codes d'activation ne sont montrés qu'une fois.
# ---------------------------------------------------------------------------

class ActivationRequest(BaseModel):
    email: EmailStr
    jeton: str = Field(min_length=10, max_length=120)
    mot_de_passe: str = Field(min_length=8, max_length=72)


class ChangerMotDePasseRequest(BaseModel):
    mot_de_passe_actuel: str = Field(min_length=1, max_length=72)
    nouveau_mot_de_passe: str = Field(min_length=8, max_length=72)


class AdminUserCreate(BaseModel):
    nom_complet: str = Field(min_length=2, max_length=255)
    email: EmailStr
    role: RoleUtilisateur
    club_id: int | None = None

    @field_validator("nom_complet")
    @classmethod
    def nom_non_vide(cls, v: str) -> str:
        nom = v.strip()
        if len(nom) < 2:
            raise ValueError("Le nom complet est trop court.")
        return nom


class AdminUserUpdate(BaseModel):
    nom_complet: str | None = Field(default=None, min_length=2, max_length=255)
    role: RoleUtilisateur | None = None
    club_id: int | None = None
    est_actif: bool | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: RoleUtilisateur
    nom_complet: str | None
    club_id: int | None
    est_actif: bool
    activation_en_attente: bool = False


class CreationCompteOut(BaseModel):
    utilisateur: AdminUserOut
    # Code à usage unique, montré UNE seule fois. Ce n'est pas un mot de
    # passe : l'utilisateur choisit son propre mot de passe à l'activation.
    jeton_activation: str
