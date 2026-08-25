from pydantic import BaseModel, ConfigDict, EmailStr

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
