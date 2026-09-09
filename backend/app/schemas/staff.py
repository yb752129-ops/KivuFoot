from pydantic import BaseModel, ConfigDict

from app.models.enums import RoleStaff, StatutJoueur


class StaffCreate(BaseModel):
    nom_complet: str
    role: RoleStaff = RoleStaff.ENTRAINEUR_PRINCIPAL


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    club_id: int
    nom_complet: str
    role: RoleStaff
    statut: StatutJoueur
    photo_url: str | None = None
