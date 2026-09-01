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
